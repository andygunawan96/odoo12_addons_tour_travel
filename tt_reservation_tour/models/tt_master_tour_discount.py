from odoo import api, fields, models, _


class TourDiscountFit(models.Model):
    _name = 'tt.master.tour.discount'
    _description = 'Master Tour Discount'

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    tour_id = fields.Many2one('tt.master.tour', 'Master Tour', readonly=True)
    min_pax = fields.Integer('Min Pax')
    max_pax = fields.Integer('Max Pax')
    pax_amount = fields.Char('Participant Amount', compute="_compute_pax_amount")
    discount_per_pax = fields.Monetary('Discount Per Pax', default=0)
    discount_total = fields.Monetary('Discount Total')

    @api.onchange('min_pax', 'max_pax')
    @api.depends('min_pax', 'max_pax')
    def _compute_pax_amount(self):
        for rec in self:
            rec.pax_amount = str(rec.min_pax) + ' - ' + str(rec.max_pax)
