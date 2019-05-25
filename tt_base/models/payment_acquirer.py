from odoo import api, fields, models, _


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    type = fields.Selection([('cash', 'Cash'), ('transfer', 'Transfer'), ('installment', 'Installment'), ('va', 'Virtual Account')],
                            'Payment Type')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    bank_id = fields.Many2one('tt.bank', 'Bank')
