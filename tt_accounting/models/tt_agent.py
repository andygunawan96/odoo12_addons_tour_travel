from odoo import models, fields, api, _
from datetime import datetime
import pytz
import logging

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
                for ledger_obj in rec.ledger_ids.search([('source_of_funds_type', '=', 'balance')]): ## source_of_funds_type 0 untuk balance
                    rec.balance = ledger_obj.balance
                    break
            else:
                rec.balance = 0

    def compute_all_agent_balance_credit_limit(self):
        for rec in self.search([]):
            rec._compute_balance_credit_limit_agent()

    @api.depends('ledger_ids','ledger_ids.balance')
    def _compute_balance_credit_limit_agent(self):
        for rec in self:
            if len(rec.ledger_ids) > 0:
                for ledger_obj in rec.ledger_ids.search([('source_of_funds_type', '=', 'credit_limit')]): ## source_of_funds_type 0 untuk balance
                    rec.balance_credit_limit = ledger_obj.balance
                    break
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
            datetime.now(pytz.timezone('Asia/Jakarta')).date(),
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