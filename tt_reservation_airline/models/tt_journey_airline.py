from odoo import api,models,fields
from ...tools import variables


class TtJourneyAirline(models.Model):
    _name = 'tt.journey.airline'
    _rec_name = 'pnr'
    _order = 'departure_date'


    provider_booking_id = fields.Many2one('tt.provider.airline', 'Provider Booking', ondelete='cascade')
    provider_id = fields.Many2one('tt.provider', related='provider_booking_id.provider_id', store=True)
    pnr = fields.Char('PNR', related='provider_booking_id.pnr', store=True)


    booking_id = fields.Many2one('tt.reservation.airline', related='provider_booking_id.booking_id', string='Order Number',
                                 store=True)
    sequence = fields.Integer('Sequence')
    journey_type = fields.Selection(variables.JOURNEY_TYPE, string='Type')
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    departure_date = fields.Datetime('Departure Date')
    arrival_date = fields.Datetime('Arrival Date')

    segment_ids = fields.One2many('tt.segment.airline', 'journey_id', 'Segments')