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

    is_vtl_flight = fields.Boolean('VTL Flight', default=False)

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

        # March 18, 2022 - SAM
        # Menambahkan journey key untuk digunakan reroute
        journey_key_list = []
        origin_code = self.origin_id.code if self.origin_id else ''
        destination_code = self.destination_id.code if self.destination_id else ''
        origin_display_name = self.origin_id.name if self.origin_id else ''
        destination_display_name = self.destination_id.name if self.destination_id else ''
        if origin_code:
            journey_key_list.append(origin_code)
        if destination_code:
            journey_key_list.append(destination_code)
        journey_key = '-'.join(journey_key_list)
        # END

        res = {
            'sequence': self.sequence,
            'origin': origin_code,
            'origin_display_name': origin_display_name,
            'destination': destination_code,
            'destination_display_name': destination_display_name,
            'journey_key': journey_key,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'segments': segment_list,
            'search_banner': search_banner_list,
            'is_vtl_flight': self.is_vtl_flight,
            'journey_code': self.journey_code if self.journey_code else ''
        }

        return res

    def compute_detail_info(self):
        if self.segment_ids:
            segment_code_list = [seg.segment_code for seg in self.segment_ids]
            journey_code = ';'.join(segment_code_list)
            self.write({
                'departure_date': self.segment_ids[0]['departure_date'],
                'arrival_date': self.segment_ids[-1]['arrival_date'],
                'journey_code': journey_code
            })
