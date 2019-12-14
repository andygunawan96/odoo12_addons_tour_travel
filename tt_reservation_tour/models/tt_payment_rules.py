from odoo import api, fields, models, _
from addons import decimal_precision as dp


class PaymentRules(models.Model):
    _name = 'tt.payment.rules'
    _order = 'due_date'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True, default='Full Payment')
    description = fields.Char('Description')
    payment_percentage = fields.Float('Payment Percentage (%)', default=0, required=True)
    due_date = fields.Date('Due Date', required=True)
    pricelist_id = fields.Many2one('tt.master.tour', 'Tour Package ID', readonly=True)
