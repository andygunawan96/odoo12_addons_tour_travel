from odoo import models, fields


class ResBank(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.bank'
    _rec_name = 'name'
    _description = 'Tour & Travel - Bank'

    name = fields.Char('Name')
    logo = fields.Binary('Bank Logo', attachment=True)
    code = fields.Char('Bank Code')
    bic = fields.Char('Bic')
    agent_bank_ids = fields.One2many('agent.bank.detail', 'bank_id', 'Agent Bank')
    company_bank_ids = fields.One2many('company.bank.detail', 'bank_id', 'Company Bank')
    customer_bank_ids = fields.One2many('customer.bank.detail', 'bank_id', 'Customer Bank')
    payment_acquirer_ids = fields.Char('Payment Acquirer')
    active = fields.Boolean('Active', default=True)
