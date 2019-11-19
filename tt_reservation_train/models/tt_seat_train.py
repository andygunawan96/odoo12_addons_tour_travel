from odoo import api, fields, models, _


class TtSeatTrain(models.Model):
    _name = 'tt.seat.train'
    _description = 'Rodex Model'

    seat = fields.Char('Seat')
    seat_code = fields.Char('Seat Code')
    journey_id = fields.Many2one('tt.journey.train', 'Segment')
    passenger_id = fields.Many2one('tt.reservation.passenger.train', 'Passenger')

    def to_dict(self):
        return {
            'seat': self.seat,
            'seat_code': self.seat_code,
            'passenger': self.passenger_id.name,
            'passenger_sequence': self.passenger_id.sequence
        }