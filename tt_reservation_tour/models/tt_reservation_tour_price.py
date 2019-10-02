from odoo import api, fields, models, _

PAX_TYPE = [
    ('adt', 'Adult'),
    ('chd', 'Child'),
    ('inf', 'Infant'),
]


class TourBookingPrice(models.Model):
    _name = 'tt.reservation.tour.price'
    _description = 'Rodex Model'

    # name = fields.Char()
    tour_id = fields.Many2one('tt.reservation.tour', 'Tour Booking')

    charge_code = fields.Char('Charge Code', default='fare', required=True)
    pax_type = fields.Selection(PAX_TYPE, 'Pax Type')
    pax_count = fields.Integer('Pax Count')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Monetary('Amount')
    total = fields.Monetary('Total')

    description = fields.Text('Description')
