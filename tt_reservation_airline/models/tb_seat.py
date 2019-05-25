from odoo import api, fields, models, _


class TransportSeat(models.Model):
    _name = 'tt.tb.seat.airline'

    seat = fields.Char('Seat')
    segment_id = fields.Many2one('tt.tb.segment.airline', 'Segment')
    passenger_id = fields.Many2one('tt.customer', 'Passenger')