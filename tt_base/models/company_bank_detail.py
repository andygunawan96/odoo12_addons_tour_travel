from odoo import models, fields, api


class CompanyBankDetail(models.Model):
    _inherit = ['tt.history']
    _name = 'company.bank.detail'
    _rec_name = 'account_number'
    _description = 'Tour & Travel - Company Bank Detail'

    account_number = fields.Char('Account Number')
    account_holder_name = fields.Char('Account Holder Name')
    bank_id = fields.Many2one('tt.bank', 'Bank')
    company_id = fields.Many2one('tt.company', 'Company')
    active = fields.Boolean('Active', default=True)
