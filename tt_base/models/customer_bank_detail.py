from odoo import models, fields, api


class CustomerBankDetail(models.Model):
    _inherit = ['tt.history']
    _name = 'customer.bank.detail'
    _rec_name = 'account_number'
    _description = 'Tour & Travel - Customer Bank Detail'

    account_number = fields.Char('Account Number')
    account_holder_name = fields.Char('Account Holder Name')
    bank_id = fields.Many2one('tt.bank', 'Bank')
    customer_id = fields.Many2one('tt.customer', 'Customer')
    active = fields.Boolean('Active', default=True)
