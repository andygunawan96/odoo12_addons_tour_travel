from odoo import api,models,fields
from .tt_reservation_train import BOOKING_STATE

JOURNEY_TYPE = [('DP', 'Depart'), ('RT', 'Return'), ('MC', 'Multi City')]

class TransportJourney(models.Model):
    _name = 'tt.tb.journey.train'
    _rec_name = 'pnr'
    # _order = 'sequence'
    _order = 'departure_date'

    provider_booking_id = fields.Many2one('tt.tb.provider.train', 'Provider Booking', ondelete='cascade')
    provider = fields.Char('Provider', related='provider_booking_id.provider', store=True)
    pnr = fields.Char('PNR', related='provider_booking_id.pnr', store=True)

    booking_id = fields.Many2one('tt.reservation.train', related='provider_booking_id.booking_id', string='Order Number',
                                 store=True)
    # sequence = fields.Integer('Sequence', compute='_compute_sequence')
    sequence = fields.Integer('Sequence')
    journey_type = fields.Selection(JOURNEY_TYPE, string='Type')
    origin = fields.Char('Origin')
    destination = fields.Char('Destination')
    # origin_id = fields.Many2one('tt.destinations', 'Origin')
    # destination_id = fields.Many2one('tt.destinations', 'Destination')
    departure_date = fields.Datetime('Departure Date')
    arrival_date = fields.Datetime('Arrival Date')

    segment_ids = fields.One2many('tt.tb.segment.train', 'journey_id', 'Segments')
    free_baggage = fields.Char('Free Baggage')
    free_meal = fields.Char('Free Meal')

    state = fields.Selection(BOOKING_STATE, 'Status', related='provider_booking_id.state', default="draft")