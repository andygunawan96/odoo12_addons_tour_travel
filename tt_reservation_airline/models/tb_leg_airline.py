from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp

from .tt_reservation_airline import BOOKING_STATE
import json
from .tb_journey_airline import JOURNEY_TYPE
from datetime import datetime


class TransportLeg(models.Model):
    _name = 'tt.tb.leg.airline'
    _order = 'sequence'

    name = fields.Char('Name', compute='_fill_name')
    leg_code = fields.Char('Leg Code')
    journey_type = fields.Selection(JOURNEY_TYPE, string='Journey Type', default='DP',
                                    states={'draft': [('readonly', False)]})
    pnr = fields.Char('PNR', related='segment_id.pnr', store=True)
    state = fields.Selection(BOOKING_STATE, 'Status', related='segment_id.state',
                             default="draft")

    carrier_id  = fields.Many2one('tt.transport.carrier','Plane')
    carrier_name = fields.Char('Flight Name')
    carrier_code = fields.Char('Flight Code')
    carrier_number = fields.Char('Flight Number')
    carrier_type = fields.Selection([()], 'Carrier Type', related='carrier_id.transport_type')
    provider = fields.Char('Provider')

    # Journey Information
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    #departure_date & arrival_date MUST CHAR TYPE, krn mengikuti user.timezone
    #departure_date_fmt & arrival_date_fmt TELAH mengikuti user.lang.format
    departure_date = fields.Char('Departure Date')
    departure_date_fmt = fields.Char('Departure Date', compute='_compute_date_fmt')

    arrival_date = fields.Char('Arrival Date')
    arrival_date_fmt = fields.Char('Arrival Date', compute='_compute_date_fmt')

    elapsed_time = fields.Char('Elapsed Time')
    class_of_service = fields.Char('Class')
    subclass = fields.Char('SubClass')
    cabin_class = fields.Char('Cabin Class')
    # agent_id = fields.Many2one('res.partner', related='segment_id.agent_id', store=True)

    sequence = fields.Integer('Sequence')

    segment_id = fields.Many2one('tt.tb.segment.airline', 'Segment', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.airline', 'Order Number', related='segment_id.booking_id', store=True)


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