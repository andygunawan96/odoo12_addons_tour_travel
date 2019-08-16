from odoo import api, fields, models, _

EXTRA_TYPE = [
    ('variable_cost', 'Variable Cost'),
    ('merchandise', 'Merchandise'),
    ('others', 'Others')
]


class TourQuotationExtra(models.Model):
    _name = 'tt.reservation.tour.quotation.extra'
    _description = 'Rodex Model'

    # tour_quotation_id = fields.Char('Tour Quotation')
    tour_quotation_id = fields.Many2one('tt.reservation.tour.package.quotation', 'Tour Quotation')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    description = fields.Text('Description')

    extra_cost = fields.Integer('Cost', default=0)
    extra_currency = fields.Char('Currency')
    extra_rate = fields.Monetary('Exchange Rate', default=1)
    extra_type = fields.Selection(EXTRA_TYPE, 'Type')
    rupiah_extra_cost = fields.Monetary('Cost (Rupiah)', default=0)
    extra_days = fields.Integer('Days', default=1)

    @api.depends('extra_cost', 'extra_rate', 'extra_days')
    @api.onchange('extra_cost', 'extra_rate', 'extra_days')
    def _compute_rupiah_extra_cost(self):
        self.rupiah_extra_cost = self.extra_cost * self.extra_rate * self.extra_days
