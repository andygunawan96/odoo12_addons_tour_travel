from odoo import api, fields, models, _

BED_TYPE = [
    ('double', 'Double/Twin'),
    ('triple', 'Triple')
]


class TourRooms(models.Model):
    _name = 'tt.tour.rooms'

    name = fields.Char('Name', required=True, default='Standard')
    bed_type = fields.Selection(BED_TYPE, 'Bed Type', default='double', required=True)
    description = fields.Text('Description')

    hotel = fields.Char('Hotel')
    address = fields.Char('Address')
    star = fields.Integer('Star')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    adult_surcharge = fields.Monetary('Adult Extra Bed Charge', default=0, required=True)
    child_surcharge = fields.Monetary('Child Extra Bed Charge', default=0, required=True)
    additional_charge = fields.Monetary('Additional Charge', default=0, help="charge for upgrade room or hotel",
                                        required=True)
    single_supplement = fields.Monetary('Single Supplement', default=0, required=True)

    pax_minimum = fields.Integer('Pax Minimum', default=0, help="required pax to avoid single sup", required=True)
    pax_limit = fields.Integer('Pax Limit', default=0, help="max pax in a room", required=True)
    adult_limit = fields.Integer('Adult Limit', default=0, help="max adult in a room", required=True)
    extra_bed_limit = fields.Integer('Extra Bed Limit', default=0, help="max extra bed in a room", required=True)

    tour_pricelist_id = fields.Many2one('tt.tour.pricelist', 'Pricelist ID', readonly=True)
