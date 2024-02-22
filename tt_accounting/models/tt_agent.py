from odoo import models, fields, api, _
from datetime import datetime
import pytz
import logging
from ...tools import util

_logger = logging.getLogger(__name__)

class TtAgent(models.Model):
    _inherit = 'tt.agent'

    ledger_ids = fields.One2many('tt.ledger', 'agent_id', 'Ledger(s)')
    balance = fields.Monetary(string="Balance", compute="_compute_balance_agent",store=True)
    adjustment_ids = fields.One2many('tt.adjustment', 'res_id', 'Adjustment Balance',
                                     domain=[('res_model', '=', 'tt.agent')])

    balance_credit_limit = fields.Monetary(string="Balance Credit Limit", compute="_compute_balance_credit_limit_agent", store=True)
    actual_credit_balance = fields.Monetary(string="Actual Credit Limit", readonly=True, compute="_compute_actual_credit_balance")  ## HANYA CREDIT LIMIT
    unprocessed_amount = fields.Monetary(string="Unprocessed Amount", readonly=True, compute="_compute_unprocessed_amount")
    limit_usage_notif = fields.Integer(string="Limit Usage Notification (%)", default=60, help="Send Email Notification when credit limit usage reaches certain percentage.")
    tax_percentage = fields.Float('Tax (%)', default=0)
    point_reward = fields.Float(string="Point Reward", compute="_compute_point_reward_agent")
    actual_point_reward = fields.Float(string="Actual Point Reward", compute="_compute_point_reward_agent")
    unprocessed_point_reward = fields.Float(string="Unprocess Point Reward", compute="_compute_point_reward_agent")

    def action_view_ledgers(self):
        return {
            'name': _('Ledger(s)'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'tt.ledger',
            'domain': [('agent_id', '=', self.id)],
            'context': {
                'form_view_ref': 'tt_accounting.tt_ledger_form_view',
                'tree_view_ref': 'tt_accounting.tt_ledger_tree_view'
            },
        }

    def compute_all_agent_balance(self):
        for rec in self.search([]):
            rec._compute_balance_agent()

    @api.depends('ledger_ids','ledger_ids.balance')
    def _compute_balance_agent(self):
        for rec in self:
            if len(rec.ledger_ids) > 0:
                ledger_obj = self.env['tt.ledger'].search([('agent_id', '=', rec.id), ('source_of_funds_type', '=', 'balance')],limit=1)
                if len(ledger_obj.ids) > 0:
                    rec.balance = ledger_obj.balance
            else:
                rec.balance = 0

    def compute_all_agent_balance_credit_limit(self):
        for rec in self.search([]):
            rec._compute_balance_credit_limit_agent()

    @api.depends('ledger_ids','ledger_ids.balance')
    def _compute_balance_credit_limit_agent(self):
        for rec in self:
            if len(rec.ledger_ids) > 0:
                ledger_obj = self.env['tt.ledger'].search([('agent_id', '=', rec.id), ('source_of_funds_type', '=', 'credit_limit')],limit=1)
                if len(ledger_obj.ids) > 0:
                    rec.balance_credit_limit = ledger_obj.balance
            else:
                rec.balance_credit_limit = 0

    def _compute_actual_credit_balance(self):
        for rec in self:
            rec.actual_credit_balance = rec.credit_limit - rec.unprocessed_amount + rec.balance_credit_limit

    def _compute_unprocessed_amount(self):
        for rec in self:
            total_amt = 0
            invoice_objs = self.env['tt.ho.invoice'].sudo().search([('agent_id', '=', rec.id), ('state', 'in', ['draft', 'confirm'])])
            for rec2 in invoice_objs:
                for rec3 in rec2.invoice_line_ids:
                    total_amt += rec3.total_after_tax

            ## check invoice billed tetapi sudah di bayar
            invoice_bill_objs = self.env['tt.ho.invoice'].sudo().search(
                [('agent_id', '=', rec.id), ('state', 'in', ['bill','bill2']), ('paid_amount','>',0)])
            paid_amount = 0
            for billed_invoice in invoice_bill_objs:
                paid_amount += billed_invoice.paid_amount
            rec.unprocessed_amount = total_amt-paid_amount


    def create_ledger_statement(self):
        ##fixing balance from last statement
        statement_ledger_obj = self.env['tt.ledger'].search([('agent_id','=',self.id),('transaction_type','=',9), ('source_of_funds_type','=','balance')],limit=1,order='id desc') ## source_of_funds_type 0 untuk balance
        dom = [('agent_id', '=', self.id)]
        beginning = True
        if statement_ledger_obj:
            dom.append(('id', '>', statement_ledger_obj.id))
        list_check_ledger_objs = self.env['tt.ledger'].search(dom,order='id asc')
        _logger.info("Agent %s %s ledger since last balance statement" % (self.name,len(list_check_ledger_objs.ids)))
        for idx,ledger in enumerate(list_check_ledger_objs):
            if beginning:
                beginning = False
                continue
            true_balance = list_check_ledger_objs[idx-1].balance + ledger.debit - ledger.credit
            if ledger.balance != true_balance:
                ledger.balance = true_balance
                _logger.info("Ledger %s ID %s from agent %s Balance Fixed" % (ledger.name,ledger.id,self.name))
        _logger.info("Start agent compute balance %s" % self.name)
        self._compute_balance_agent()
        _logger.info("End agent compute balance %s" % self.name)

        _logger.info("Start create ledger statement %s" % self.name)
        ##create ledger statement
        self.env['tt.ledger'].create_ledger_vanilla(
            self._name,
            self.id,
            'End Balance Statement %s' % (self.name),
            self.seq_id,
            9,
            self.currency_id.id,
            self.env.ref('base.user_root').id,
            self.id,
            False,
            0,
            0,
            'Automatic End Balance Statement'
        )
        _logger.info("End create ledger statement %s" % self.name)


    def _compute_all_actual_point_reward_agent(self):
        for rec in self.search([]):
            rec._compute_actual_point_reward_agent()

    def _compute_actual_point_reward_agent(self):
        self.actual_point_reward = self.point_reward - self.unprocessed_point_reward

    #_compute_unprocessed_point_reward
    def _compute_all_unprocessed_point_reward(self):
        for rec in self.search([]):
            rec._compute_unprocessed_point_reward()

    def _compute_unprocessed_point_reward(self):
        total_amt = 0
        payment_acq_number_objs = self.env['payment.acquirer.number'].sudo().search([('agent_id', '=', self.id), ('state', 'in', ['close', 'waiting']),('is_using_point_reward', '=', True)])
        for payment_acq_number_obj in payment_acq_number_objs:
            total_amt += payment_acq_number_obj.point_reward_amount
        invoice_ho_objs = self.env['tt.ho.invoice'].search([('agent_id', '=', self.id), ('state', '=', 'confirm')])
        for invoice_obj in invoice_ho_objs:
            for invoice_line_obj in invoice_obj.invoice_line_ids:
                for invoice_line_detail_obj in invoice_line_obj.invoice_line_detail_ids:
                    if invoice_line_detail_obj.is_point_reward:
                        total_amt += invoice_line_detail_obj.price_unit
        self.unprocessed_point_reward = total_amt

    def _compute_all_point_reward_agent(self):
        for rec in self.search([]):
            rec._compute_point_reward_agent()

    @api.depends('ledger_ids', 'ledger_ids.balance')
    def _compute_point_reward_agent(self):
        for rec in self:
            point_reward = 0
            ### POINT REWARD ####
            if len(rec.ledger_ids)>0:
                ledger_obj = self.env['tt.ledger'].search([('agent_id', '=', rec.id), ('source_of_funds_type', '=', 'point')], limit=1)
                if len(ledger_obj.ids) > 0:
                    point_reward = ledger_obj.balance
            rec.point_reward = point_reward

            ### UNPROCESS AMOUNT ####
            rec._compute_unprocessed_point_reward()

            ### ACTUAL POINT REWARD ###
            rec._compute_actual_point_reward_agent()


    # kalau pakai cron sementara tidak di pakai
    def create_point_reward_statement(self):
        statement_ledger_obj = self.env['tt.ledger'].search(
            [('agent_id', '=', self.id), ('transaction_type', '=', 9), ('source_of_funds_type', '=', 'point')], limit=1,
            order='id desc')  ## source_of_funds_type 1 untuk points
        dom = [('agent_id', '=', self.id)]
        beginning = True
        if statement_ledger_obj:
            dom.append(('id', '>', statement_ledger_obj.id))
        list_check_ledger_objs = self.env['tt.ledger'].search(dom, order='id asc')
        _logger.info(
            "Agent %s %s ledger since last balance statement" % (self.name, len(list_check_ledger_objs.ids)))
        for idx, ledger in enumerate(list_check_ledger_objs):
            if beginning:
                beginning = False
                continue
            true_balance = list_check_ledger_objs[idx - 1].balance + ledger.debit - ledger.credit
            if ledger.balance != true_balance:
                ledger.balance = true_balance
                _logger.info("Ledger %s ID %s from agent %s Balance Fixed" % (ledger.name, ledger.id, self.name))
        self._compute_point_reward_agent()

        ##create ledger statement
        self.env['tt.ledger'].create_ledger_vanilla(
            self._name,
            self.id,
            'End Balance Statement %s' % (self.name),
            self.seq_id,
            9,
            self.currency_id.id,
            self.env.ref('base.user_root').id,
            self.id,
            False,
            0,
            0,
            'Automatic End Points Statement',
            'point'
        )

    def check_credit_limit_usage(self):
        current_perc = self.actual_credit_balance / self.credit_limit * 100
        if 100-current_perc >= self.limit_usage_notif:
            return 'You have used more than %s percent of your credit limit. Remaining Credit: %s %s / %s %s' % (self.limit_usage_notif, self.currency_id.name,
                                                                                                                 util.get_rupiah(self.actual_credit_balance), self.currency_id.name,
                                                                                                                 util.get_rupiah(self.credit_limit))
        else:
            return 'Remaining Credit: %s %s / %s %s' % (self.currency_id.name, util.get_rupiah(self.actual_credit_balance), self.currency_id.name, util.get_rupiah(self.credit_limit))
