from odoo import api, fields, models, _

BED_TYPE = [
    ('double', 'Double/Twin'),
    ('triple', 'Triple')
]


class TourRooms(models.Model):
    _name = 'tt.master.tour.rooms'
    _description = 'Master Tour Rooms'

    name = fields.Char('Name', required=True, default='Standard')
    room_code = fields.Char('Room Code', readonly=True, copy=False)
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

    pax_minimum = fields.Integer('Pax Minimum', default=0, help="required pax to avoid single sup", required=True)
    pax_limit = fields.Integer('Pax Limit', default=0, help="max pax in a room", required=True)
    adult_limit = fields.Integer('Adult Limit', default=0, help="max adult in a room", required=True)
    extra_bed_limit = fields.Integer('Extra Bed Limit', default=0, help="max extra bed in a room", required=True)

    tour_pricelist_id = fields.Many2one('tt.master.tour', 'Master Tour', readonly=True)
    tour_pricing_ids = fields.One2many('tt.master.tour.pricing', 'room_id', 'Tour Pricing')

    sequence = fields.Integer('Sequence', required=True, default=50)
    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals):
        if not vals.get('room_code'):
            vals['room_code'] = self.env['ir.sequence'].next_by_code('master.tour.room.code') or 'New'
        return super(TourRooms, self).create(vals)

    def check_confirm_validity(self):
        is_valid = False
        for rec in self.tour_pricing_ids:
            if rec.active and 0 <= rec.min_pax < 2:
                is_valid = True
        return is_valid
