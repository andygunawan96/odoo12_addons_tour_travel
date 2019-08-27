from odoo import api,fields,models
from random import randint
from datetime import datetime,timedelta
from ...tools import ERR
import logging,traceback

_logger = logging.getLogger(__name__)


class TopUpAmount(models.Model):
    _name = 'tt.top.up.amount'

    seq_id = fields.Char('Sequence ID')
    name = fields.Char('Description')
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.user.company_id.currency_id,
                                  string="Currency", readonly=True, required=True)
    amount = fields.Monetary(string='Amount')
    active = fields.Boolean('Active', default='True')

    # API FUNCTION
    def get_top_up_amount(self):
        def compute_top_up_amount(rec):
            return {
                'seq_id': rec.seq_id,
                'name': rec.name,
                'amount': rec.amount,
                'currency_code': rec.currency_id.name
            }
        return [compute_top_up_amount(rec) for rec in self.search([], order="amount")]

    def get_top_up_amount_api(self, api_context=None):
        try:
            data = self.get_top_up_amount()
            res = {
                'error_code': 0,
                'error_msg': '',
                'response': data,
            }
        except Exception as e:
            _logger.error(str(e)+traceback.format_exc())
            res = {
                'error_code': 500,
                'error_msg': str(e),
                'response': ''
            }
        return res

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.top.up.amount')
        return super(TopUpAmount, self).create(vals_list)

class TtTopUp(models.Model):
    _name = 'tt.top.up'
    _order = 'id desc'
    _description = 'Rodex Model'

    name = fields.Char('Document Number', required='True', readonly=True, states={'draft': [('readonly', False)]},
                       index=True, default=lambda self: 'New')
    date = fields.Datetime('Date', readonly=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    due_date = fields.Datetime('Due Date', readonly=True)
    agent_id = fields.Many2one('tt.agent', string="Agent", required=True, readonly=False,
                               default=lambda self: self.env.user.agent_id)
    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('confirm', 'Request'), ('valid', 'Validated'), ('done', 'Done'), ('cancel', 'Cancelled')],
                             string='State', default='draft',
                             help='''
                             Open, after submit and choose payment method
                             Request, requested top-up by agent
                             Confirm, transfared top-up amount by agent
                             Validate, top-up was check by top-up receiver
                             Paid, top-up was clearing and approve by top-up receiver
                             ''')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  related='amount_id.currency_id', store=True)
    amount_id = fields.Many2one('tt.top.up.amount', 'Amount', required=False, states={'draft': [('readonly', False)]}, readonly=True)
    amount_count = fields.Integer('TopUp Count', default=1, states={'draft': [('readonly', False)]}, readonly=True)
    amount = fields.Monetary('Unit Amount', related='amount_id.amount', store=True)
    unique_amount = fields.Monetary('Unique Amount', default=0,
                                 states={'draft': [('readonly', False)]},
                                    help='''Unique amount for identification agent top-up via wire transfer''')
    fees = fields.Monetary('Fees',  default=0, help='Fees amount; set by the system because depends on the acquirer')
    total = fields.Monetary('Total', compute='_compute_amount', store=True, readonly=True)
    total_with_fees = fields.Monetary('Total + fees', compute='_compute_amount', store=False)
    ledger_id = fields.Many2one('tt.ledger', string='Ledger', readonly=True, copy=False)
    payment_acquirer_id = fields.Many2one('payment.acquirer','Payment Type')
    validate_uid = fields.Many2one('res.users','Validate UID')
    validate_date = fields.Datetime('Validate Date')


    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.top.up')
        vals_list['due_date'] = datetime.now() + timedelta(hours=3)
        return super(TtTopUp, self).create(vals_list)

    @api.depends('amount_id', 'amount', 'amount_count', 'unique_amount', 'fees')#'amount_fix_va'
    def _compute_amount(self):
        for tp in self:
            # if tp.amount_fix_va:
            #     tp.update({
            #         'total': tp.amount_fix_va,
            #         'total_with_fees': tp.amount_fix_va + tp.fees,
            #     })
            # else:
            tp.update({
                'total': tp.amount_count * tp.amount_id.amount + tp.unique_amount,
                'total_with_fees': tp.amount_count * tp.amount_id.amount + tp.unique_amount + tp.fees,
            })

    def action_confirm(self,data):
        self.write({
            'state': 'confirm',
            'payment_acquirer_id': self.env['payment.acquirer'].search([('seq_id','=',data['payment_seq_id'])]).id
        })

    def action_request(self,data):
        self.write({
            'state': 'request',
        })

    def generate_unique_amount(self):
        random = randint(1, 333)
        return random

    def action_validate(self):
        print("validate")
        if self.state != 'request':
            raise UserWarning('Can only validate request state Top Up.')

        ledger_obj = self.env['tt.ledger']
        vals = ledger_obj.prepare_vals(self.name,self.name,datetime.now(),1,self.currency_id.id,self.total)
        vals['agent_id'] = self.agent_id.id
        new_aml = ledger_obj.create(vals)
        self.write({
            'state':'valid',
            'ledger_id': new_aml.id,
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now()
        })

    # {
    #     'name': 'New',
    #     'currency_code': '?',
    #     'amount_seq_id': 'TUA.010101',
    #     'amount_count': 5,
    #     'unique_amount': 212,
    #     'fees': 0,
    # }

    def to_dict(self):
        res = {
            'name': self.name,
            'currency_code': self.currency_id and self.currency_id.name or '',
            'date': self.date and self.date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'due_date': self.due_date and self.due_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'total': self.total or '',
            'state': self.state
        }
        return res

    def create_top_up_api(self,data,context):
        try:
            agent_obj = self.browse(context['co_agent_id'])
            if not agent_obj:
                ERR.get_error(1008)
            data.update({
                'name': self.env['ir.sequence'].next_by_code('tt.top.up.amount'),
                'state': 'open',
                'agent_id': agent_obj.id,
                'currency_id': self.env['res.currency'].search([('name','=',data.pop('currency_code'))]).id,
                'amount_id': self.env['tt.top.up.amount'].search([('seq_id','=',data.pop('amount_seq_id'))]).id,
                # 'payment_acquirer_id': self.env['payment.acquirer'].search([('seq_id','=',data.pop('payment_seq_id'))])
            })
            new_top_up = self.create(data)
            return ERR.get_no_error({
                'name': new_top_up.name
            })
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(500)

    def get_top_up_api(self,context):
        try:
            agent_obj = self.browse(context['co_agent_id'])
            if not agent_obj:
                ERR.get_error(1008)

            res = []
            for rec in self.search([('agent_id','=',agent_obj.id)]):
                res.append(rec.to_dict())

            return ERR.get_no_error(res)

        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(500)

    def confirm_top_up_api(self,data,context):
        try:
            agent_obj = self.browse(context['co_agent_id'])
            if not agent_obj:
                ERR.get_error(1008)

            top_up_obj = self.search([('name','=',data['name'])])
            if not top_up_obj:
                ERR.get_error(1010)
            if top_up_obj.state in ['request,validate,done']:
                raise ('cannot confirm already requested Top Up.')

            top_up_obj.action_confirm(data)

            return ERR.get_no_error()

        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(500)

    def request_top_up_api(self,data,context):
        try:
            agent_obj = self.browse(context['co_agent_id'])
            if not agent_obj:
                ERR.get_error(1008)

            top_up_obj = self.search([('name','=',data['name'])])
            if not top_up_obj:
                ERR.get_error(1010)

            top_up_obj.action_request(data) # ubah ke status request

            return ERR.get_no_error()

        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(500)