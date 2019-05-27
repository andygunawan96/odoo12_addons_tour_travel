from odoo import api, fields, models, _


class TourQuotationPorter(models.Model):
    _name = 'tt.tour.quotation.porter'

    tour_quotation_id = fields.Char('Tour Package Quotation')
    # tour_quotation_id = fields.Many2one('tt.tour.package.quotation', 'Tour Quotation')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    porter_cost = fields.Monetary('Porter Cost', default=0)
    porter_currency = fields.Char('Porter Currency')
    porter_rate = fields.Monetary('Porter Rate', default=1)
    rupiah_porter_cost = fields.Monetary('Rupiah Porter Cost', default=0)
    porter_days = fields.Integer('Porter Days', default=1)

    @api.depends('porter_cost', 'porter_rate', 'porter_days')
    @api.onchange('porter_cost', 'porter_rate', 'porter_days')
    def _compute_rupiah_porter_cost(self):
        self.rupiah_porter_cost = self.porter_cost * self.porter_rate * self.porter_days
