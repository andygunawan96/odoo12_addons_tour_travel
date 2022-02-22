from odoo import api,models,fields
from ...tools import variables


class TtJourneyAirline(models.Model):
    _name = 'tt.journey.airline'
    _rec_name = 'pnr'
    _order = 'departure_date'
    _description = 'Journey Airline'

    provider_booking_id = fields.Many2one('tt.provider.airline', 'Provider Booking', ondelete='cascade')
    provider_id = fields.Many2one('tt.provider', related='provider_booking_id.provider_id', store=True)
    pnr = fields.Char('PNR', related='provider_booking_id.pnr', store=True)


    booking_id = fields.Many2one('tt.reservation.airline', related='provider_booking_id.booking_id', string='Order Number',
                                 store=True)
    sequence = fields.Integer('Sequence')
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    departure_date = fields.Char('Departure Date')
    arrival_date = fields.Char('Arrival Date')
    journey_code = fields.Char('Journey Code', default='')

    segment_ids = fields.One2many('tt.segment.airline', 'journey_id', 'Segments')

    banner_ids = fields.One2many('tt.banner.airline', 'journey_id', 'Segments')

    def _compute_journey_code(self):
        for rec in self:
            if not rec.journey_code:
                journey_list = []
                for seg in rec.segment_ids:
                    if not seg.segment_code:
                        continue
                    journey_list.append(seg.segment_code)

                journey_code = ';'.join(journey_list)
                rec.write({'journey_code': journey_code})

    def to_dict(self):
        segment_list = []
        search_banner_list = []
        for rec in self.segment_ids:
            segment_list.append(rec.to_dict())
        for rec in self.banner_ids:
            search_banner_list.append(rec.to_dict())
        res ={
            'sequence': self.sequence,
            'origin': self.origin_id.code,
            'destination': self.destination_id.code,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'segments': segment_list,
            'search_banner': search_banner_list,
            'journey_code': self.journey_code if self.journey_code else ''
        }

        return res

    def compute_detail_info(self):
        segment_code_list = [seg.segment_code for seg in self.segment_ids]
        journey_code = ';'.join(segment_code_list)
        self.write({
            'departure_date': self.segment_ids[0]['departure_date'],
            'arrival_date': self.segment_ids[-1]['arrival_date'],
            'journey_code': journey_code
        })
