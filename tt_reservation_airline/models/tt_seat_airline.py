from odoo import api, fields, models, _


class TtSeatAirline(models.Model):
    _name = 'tt.seat.airline'
    _description = 'Rodex Model'

    seat = fields.Char('Seat')
    segment_id = fields.Many2one('tt.segment.airline', 'Segment')
    passenger_id = fields.Many2one('tt.customer', 'Passenger')