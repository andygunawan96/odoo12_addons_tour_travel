from odoo import api, fields, models, _


class TtSeatAirline(models.Model):
    _name = 'tt.seat.airline'
    _description = 'Seat Airline'

    seat = fields.Char('Seat')
    segment_id = fields.Many2one('tt.segment.airline', 'Segment')
    passenger_id = fields.Many2one('tt.reservation.passenger.airline', 'Passenger')