from odoo import api, fields, models, _

TYPE = [
    ('debit', 'Debit'),
    ('credit', 'Credit')
]


class TourAdjustment(models.Model):
    _name = 'tt.master.tour.adjustment'
    _description = 'Master Tour Adjustment'

    description = fields.Text('Description')
    type = fields.Selection(TYPE, 'Type')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Integer('Amount', default=1)
    price = fields.Monetary('Price', default=0, required=True)
    total = fields.Monetary('Total')

    tour_pricelist_id = fields.Many2one('tt.master.tour', 'Master Tour', readonly=True)
