from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from ...tools import variables
import json
from datetime import datetime


class TtSegmentAirline(models.Model):
    _name = 'tt.segment.airline'
    _rec_name = 'name'
    _order = 'departure_date'
    _description = 'Rodex Model'

    name = fields.Char('Name', compute='_fill_name')
    segment_code = fields.Char('Segment Code')
    fare_code = fields.Char('Fare Code')
    journey_type = fields.Selection(variables.JOURNEY_TYPE, string='Journey Type', default='DEP',
                                    states={'draft': [('readonly', False)]})

    pnr = fields.Char('PNR', related='journey_id.pnr', store=True)

    carrier_id  = fields.Many2one('tt.transport.carrier','Plane')
    carrier_code = fields.Char('Flight Code')
    carrier_number = fields.Char('Flight Number')
    provider_id = fields.Many2one('tt.provider','Provider')

    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')

    origin_terminal = fields.Char('Origin Terminal')
    destination_terminal = fields.Char('Destination Terminal')

    departure_date = fields.Char('Departure Date')
    arrival_date = fields.Char('Arrival Date')

    elapsed_time = fields.Char('Elapsed Time')

    class_of_service = fields.Char('Class')
    cabin_class = fields.Char('Cabin Class')
    # agent_id = fields.Many2one('res.partner', related='booking_id.agent_id', store=True)

    sequence = fields.Integer('Sequence')

    journey_id = fields.Many2one('tt.journey.airline', 'Journey', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.airline', 'Order Number', related='journey_id.booking_id', store=True)

    # additional_service_charge_ids = fields.One2many('tt.tb.service.charge', 'segment_id')
    seat_ids = fields.One2many('tt.seat.airline', 'segment_id', 'Seat')
    leg_ids = fields.One2many('tt.leg.airline', 'segment_id', 'Legs')

    @api.multi
    @api.depends('carrier_id')
    def _fill_name(self):
        for rec in self:
            rec.name = "%s - %s" % (rec.carrier_code,rec.carrier_number)

    def to_dict(self):
        leg_list = []
        for rec in self.leg_ids:
            leg_list.append(rec.to_dict())
        res = {
            'segment_code': self.segment_code,
            'fare_code': self.fare_code,
            'journey_type': self.journey_type,
            'pnr': self.pnr,
            'carrier_name': self.carrier_id.name,
            'carrier_code': self.carrier_code,
            'carrier_number': self.carrier_number,
            'provider': self.provider_id.code,
            'origin': self.origin_id.code,
            'origin_terminal': self.origin_terminal,
            'destination': self.destination_id.code,
            'destination_terminal': self.destination_terminal,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'elapsed_time': self.elapsed_time and self.elapsed_time or '',
            'class_of_service': self.class_of_service and self.class_of_service or '',
            'cabin_class': self.cabin_class and self.cabin_class or '',
            'sequence': self.sequence,
            'seats': [],
            'legs': leg_list
        }

        return res