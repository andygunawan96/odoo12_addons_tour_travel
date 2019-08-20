from odoo import api,fields,models
from random import randint
from datetime import datetime
class TopUpAmount(models.Model):
    _name = 'tt.top.up.amount'

    name = fields.Char('Description')
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.user.company_id.currency_id,
                                  string="Currency", readonly=True, required=True)
    amount = fields.Monetary(string='Amount')
    active = fields.Boolean('Active', default='True')

    # API FUNCTION
    def get_top_up_amount(self, api_context=None):
        def compute_top_up_amount(rec):
            return {
                'id': rec.id,
                'name': rec.name,
                'amount': rec.amount,
            }
        return [compute_top_up_amount(rec) for rec in self.search([], order="amount")]

    def get_top_up_amount_api(self, api_context=None):
        try:
            data = self.get_top_up_amount(api_context)
            res = {
                'error_code': 0,
                'error_msg': '',
                'response': data,
            }
        except Exception as e:
            res = {
                'error_code': 500,
                'error_msg': str(e),
                'response': ''
            }
        return res

class TtTopUp(models.Model):
    _name = 'tt.top.up'
    _order = 'id desc'
    _description = 'Rodex Model'

    name = fields.Char('Document Number', required='True', readonly=True, states={'draft': [('readonly', False)]},
                       index=True, default=lambda self: 'New')
    date = fields.Datetime('Date', readonly=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
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

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.top.up')
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

    def generate_unique_amount(self):
        random = randint(1, 333)
        return random

    def validate(self):
        print("validate")
        ledger_obj = self.env['tt.ledger']

        # def prepare_vals(self, name, ref, date, ledger_type, currency_id, debit=0, credit=0):
        vals = ledger_obj.prepare_vals(self.name,self.name,datetime.now(),1,self.currency_id.id,self.total)
        vals['agent_id'] = self.agent_id.id
        ledger_obj.create(vals)
        self.write({
            'state':'valid'
        })

