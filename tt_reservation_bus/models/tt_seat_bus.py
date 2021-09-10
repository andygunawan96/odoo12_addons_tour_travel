from odoo import api, fields, models, _


class TtSeatBus(models.Model):
    _name = 'tt.seat.bus'
    _description = 'Seat Bus'

    seat = fields.Char('Seat')
    seat_code = fields.Char('Seat Code')##auto findketika req parser assign seat KAI..
    journey_id = fields.Many2one('tt.journey.bus', 'Journey')
    passenger_id = fields.Many2one('tt.reservation.passenger.bus', 'Passenger')

    def to_dict(self):
        return {
            'seat': self.seat,
            'seat_code': self.seat_code,
            'passenger': self.passenger_id.name,
            'passenger_sequence': self.passenger_id.sequence
        }
