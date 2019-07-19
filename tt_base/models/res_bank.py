from odoo import models, fields


class ResBank(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.bank'
    _rec_name = 'name'
    _description = 'Tour & Travel - Bank'

    name = fields.Char('Name')
    logo = fields.Binary('Bank Logo', attachment=True)
    code = fields.Char('Bank Code')
    bic = fields.Char('Bank Identifier Code', help='BIC / Swift')
    agent_bank_ids = fields.One2many('agent.bank.detail', 'bank_id', 'Agent Bank')
    customer_bank_ids = fields.One2many('customer.bank.detail', 'bank_id', 'Customer Bank')
    payment_acquirer_ids = fields.One2many('payment.acquirer', 'bank_id', 'Payment Acquirer')
    active = fields.Boolean('Active', default=True)
    image = fields.Binary('Bank Logo', attachment=True)
