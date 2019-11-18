from odoo import api, fields, models, _
from addons import decimal_precision as dp


class PaymentRules(models.Model):
    _name = 'tt.payment.rules'
    _order = 'due_date'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True, default='Payment')
    description = fields.Char('Description')
    payment_type = fields.Selection([('percentage', 'Percentage'), ('amount', 'Amount')], 'Payment Type', default="percentage")
    payment_percentage = fields.Float('Payment Percentage (%)', default=0)
    payment_amount = fields.Float('Payment Amount', default=0)
    due_date = fields.Date('Due Date', required=True)
    pricelist_id = fields.Many2one('tt.master.tour', 'Tour Package ID', readonly=True)
