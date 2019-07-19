from odoo import api, fields, models, _
from ...tools import variables
import odoo.addons.decimal_precision as dp
import json
from datetime import datetime


class TtLegAirline(models.Model):
    _name = 'tt.leg.airline'
    _order = 'sequence'

    leg_code = fields.Char('Leg Code')
    journey_type = fields.Selection(variables.JOURNEY_TYPE, string='Journey Type', default='DEP',
                                    states={'draft': [('readonly', False)]})
    pnr = fields.Char('PNR', related='segment_id.pnr', store=True)

    carrier_id = fields.Many2one('tt.transport.carrier','Plane')
    carrier_code = fields.Char('Flight Code')
    carrier_number = fields.Char('Flight Number')
    provider_id = fields.Many2one('tt.provider','Provider')

    # Journey Information
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    departure_date = fields.Char('Departure Date')

    arrival_date = fields.Char('Arrival Date')

    elapsed_time = fields.Char('Elapsed Time')
    class_of_service = fields.Char('Class')
    subclass = fields.Char('SubClass')
    cabin_class = fields.Char('Cabin Class')
    # agent_id = fields.Many2one('res.partner', related='segment_id.agent_id', store=True)

    sequence = fields.Integer('Sequence')

    segment_id = fields.Many2one('tt.segment.airline', 'Segment', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.airline', 'Order Number', related='segment_id.booking_id', store=True)