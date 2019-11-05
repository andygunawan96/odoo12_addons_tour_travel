from odoo import api, fields, models, _


class TtSeatTrain(models.Model):
    _name = 'tt.seat.train'
    _description = 'Rodex Model'

    seat = fields.Char('Seat')
    segment_id = fields.Many2one('tt.journey.train', 'Segment')
    passenger_id = fields.Many2one('tt.passenger', 'Passenger')