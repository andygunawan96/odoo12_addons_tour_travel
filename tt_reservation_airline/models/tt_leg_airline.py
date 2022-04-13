from odoo import api, fields, models, _
from ...tools import variables
import json
from datetime import datetime


class TtLegAirline(models.Model):
    _name = 'tt.leg.airline'
    _order = 'sequence'
    _description = 'Leg Airline'

    leg_code = fields.Char('Leg Code')

    provider_id = fields.Many2one('tt.provider','Provider')

    # Journey Information
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')

    origin_terminal = fields.Char('Origin Terminal')
    destination_terminal = fields.Char('Destination Terminal')

    departure_date = fields.Char('Departure Date')
    arrival_date = fields.Char('Arrival Date')

    elapsed_time = fields.Char('Elapsed Time')
    # agent_id = fields.Many2one('res.partner', related='segment_id.agent_id', store=True)

    sequence = fields.Integer('Sequence')

    segment_id = fields.Many2one('tt.segment.airline', 'Segment', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.airline', 'Order Number', related='segment_id.booking_id', store=True)

    def to_dict(self):
        res = {
            'leg_code': self.leg_code,
            'origin': self.origin_id and self.origin_id.code or '',
            'destination': self.destination_id and self.destination_id.code or '',
            'origin_terminal': self.origin_terminal and self.origin_terminal or '',
            'destination_terminal': self.destination_terminal and self.destination_terminal or '',
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'elapsed_time': self.elapsed_time and self.elapsed_time or '',
            'sequence': self.sequence
        }
        return res