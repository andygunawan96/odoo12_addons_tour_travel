from odoo import api,models,fields
from ...tools import variables


class TtJourneyTrain(models.Model):
    _name = 'tt.journey.train'
    _rec_name = 'pnr'
    _order = 'departure_date'
    _description = 'Rodex Model'

    provider_booking_id = fields.Many2one('tt.provider.train', 'Provider Booking', ondelete='cascade')
    provider_id = fields.Many2one('tt.provider', related='provider_booking_id.provider_id', store=True)
    pnr = fields.Char('PNR', related='provider_booking_id.pnr', store=True)


    booking_id = fields.Many2one('tt.reservation.train', related='provider_booking_id.booking_id', string='Order Number',
                                 store=True)
    sequence = fields.Integer('Sequence')
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    departure_date = fields.Char('Departure Date')
    arrival_date = fields.Char('Arrival Date')

    def to_dict(self):
        segment_list = []
        for rec in self.segment_ids:
            segment_list.append(rec.to_dict())
        res ={
            'sequence': self.sequence,
            'origin': self.origin_id.code,
            'destination': self.destination_id.code,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'segments': segment_list
        }

        return res