from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp

from .tt_reservation_airline import BOOKING_STATE
import json
from .tb_journey_airline import JOURNEY_TYPE
from datetime import datetime


class TransportSegment(models.Model):
    _name = 'tt.tb.segment.airline'
    _order = 'sequence'

    name = fields.Char('Name', compute='_fill_name')
    segment_key = fields.Char('Segment Key')
    segment_code = fields.Char('Segment Code')
    fare_code = fields.Char('Fare Code')
    journey_type = fields.Selection(JOURNEY_TYPE, string='Journey Type', default='DP',
                                    states={'draft': [('readonly', False)]})
    # booking_code = fields.Char('Booking Code')

    pnr = fields.Char('PNR', related='journey_id.pnr', store=True)
    airline_pnr_ref = fields.Char('Airline PNR Ref')
    state = fields.Selection(BOOKING_STATE, 'Status', related='journey_id.state', default="draft")

    carrier_id  = fields.Many2one('tt.transport.carrier','Plane')
    carrier_name = fields.Char('Flight Name')
    carrier_code = fields.Char('Flight Code')
    carrier_number = fields.Char('Flight Number')
    carrier_type = fields.Selection([()], 'Carrier Type', related='carrier_id.transport_type')
    provider = fields.Char('Provider')

    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')

    departure_date = fields.Char('Departure Date')
    departure_date_fmt = fields.Char('Departure Date', compute='_compute_date_fmt')

    arrival_date = fields.Char('Arrival Date')
    arrival_date_fmt = fields.Char('Arrival Date', compute='_compute_date_fmt')

    elapsed_time = fields.Char('Elapsed Time')
    class_of_service = fields.Char('Class')
    subclass = fields.Char('SubClass')
    cabin_class = fields.Char('Cabin Class')
    # agent_id = fields.Many2one('res.partner', related='booking_id.agent_id', store=True)

    sequence = fields.Integer('Sequence')
    sequence_segment = fields.Integer('Sequence Segment')
    sequence_leg = fields.Integer('Sequence Leg')

    journey_id = fields.Many2one('tt.tb.journey.airline', 'Journey', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.airline', 'Order Number', related='journey_id.booking_id', store=True)

    # additional_service_charge_ids = fields.One2many('tt.tb.service.charge', 'segment_id')
    seat_ids = fields.One2many('tt.tb.seat.airline', 'segment_id', 'Seat')
    leg_ids = fields.One2many('tt.tb.leg.airline', 'segment_id', 'Legs')

    @api.multi
    @api.depends('carrier_name')
    def _fill_name(self):
        for rec in self:
            rec.name = "%s - %s" % (rec.pnr, rec.carrier_name)

    def _compute_date_fmt(self):
        lang = self.env['res.lang']._lang_get(self.env.user.lang)
        for rec in self:
            rec.departure_date_fmt = rec.departure_date and datetime.strptime(rec.departure_date,
                                                                              '%Y-%m-%d %H:%M:%S').strftime(
                "%s %s" % (lang.date_format, lang.time_format)) or ''
            rec.arrival_date_fmt = rec.arrival_date and datetime.strptime(rec.arrival_date,
                                                                          '%Y-%m-%d %H:%M:%S').strftime(
                "%s %s" % (lang.date_format, lang.time_format)) or ''
