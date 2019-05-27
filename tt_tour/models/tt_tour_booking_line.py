from odoo import api, fields, models, _

PAX_TYPE = [
    ('adt', 'Adult'),
    ('chd', 'Child'),
    ('inf', 'Infant')
]

BED_TYPE = [
    ('single', 'Single'),
    ('double', 'Double'),
    ('triple', 'Triple'),
]


class TourBookingLine(models.Model):
    _name = 'tt.tour.booking.line'

    tour_booking_id = fields.Many2one('tt.tour.booking', 'Tour Booking')

    passenger_id = fields.Many2one('tt.customer', 'Passenger')
    pax_type = fields.Selection(PAX_TYPE, 'Pax Type')
    pax_mobile = fields.Char('Pax Mobile')

    room_id = fields.Char('Room ID')
    # room_id = fields.Many2one('tt.tour.rooms', 'Tour ID')
    room_number = fields.Char('Room Number')
    extra_bed_description = fields.Char('Extra Bed Description')
    bed_type = fields.Selection(BED_TYPE, 'Bed Type')
    description = fields.Char('Description')
    tour_pricelist_id = fields.Many2one('tt.tour.pricelist', 'Pricelist ID')
    state = fields.Selection([], related='tour_booking_id.state')
