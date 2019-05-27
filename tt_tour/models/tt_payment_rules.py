from odoo import api, fields, models, _
from addons import decimal_precision as dp


class PaymentRules(models.Model):
    _name = 'tt.payment.rules'
    _order = 'due_date'

    name = fields.Char('Name', required=True, default='Payment')
    description = fields.Char('Description')
    payment_percentage = fields.Float('Payment Percentage (%)', digits=dp.get_precision('Payment Terms'), required=True)
    due_date = fields.Date('Due Date', required=True)
    pricelist_id = fields.Many2one('tt.tour.pricelist', 'Pricelist ID', readonly=True)
