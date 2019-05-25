from odoo import api, fields, models, _


class TransportSeat(models.Model):
    _name = 'tt.tb.seat.train'

    seat = fields.Char('Seat')
    seat_code = fields.Char('Seat Code')
    segment_id = fields.Many2one('tt.tb.segment.train', 'Segment')
    passenger_id = fields.Many2one('tt.customer', 'Passenger')