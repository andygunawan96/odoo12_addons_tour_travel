from odoo import api,models,fields
from ...tools import variables


class TtJourneyTrain(models.Model):
    _name = 'tt.journey.train'
    _rec_name = 'pnr'
    _order = 'departure_date'
    _description = 'Journey Train'

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

    carrier_id = fields.Many2one('tt.transport.carrier','Carrier')
    carrier_code = fields.Char('Carrier Code')
    carrier_number = fields.Char('Carrier Number')
    carrier_name = fields.Char('Carrier Name')
    journey_code = fields.Char('Journey Code')
    fare_code = fields.Char('Fare Code')

    seat_ids = fields.One2many('tt.seat.train','journey_id','Seat')
    cabin_class = fields.Char('Cabin Class')
    class_of_service = fields.Char('Class of Service')

    def to_dict(self):
        seat_list = []
        for rec in self.seat_ids:
            seat_list.append(rec.to_dict())
        res ={
            'sequence': self.sequence,
            'origin': self.origin_id.code,
            'destination': self.destination_id.code,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'pnr': self.pnr,

            'carrier_code': self.carrier_code,
            'carrier_number': self.carrier_number,
            'carrier_name': self.carrier_name,
            'journey_code': self.journey_code,
            'fare_code': self.fare_code,

            'seats': seat_list,
            'cabin_class': self.cabin_class,
            'class_of_service': self.class_of_service
        }

        return res

    def create_seat(self,seats):
        seat_list = []
        for seat in seats:
            if not self.seat_ids.filtered(lambda x: x.seat_code == str(seat['seat_code'])):
                seat_list.append((0,0,{
                    'seat': seat['seat'],
                    'seat_code': seat['seat_code'],
                    'journey_id': self.id,
                    'passenger_id': self.booking_id.passenger_ids.filtered(lambda x: x.sequence == seat.get('sequence')).id
                }))
        self.write({
            'seat_ids':seat_list
        })

    def update_ticket(self,seats):
        for seat in seats:
            curr_seat = self.seat_ids.filtered(lambda x: x.passenger_id.sequence == seat['passenger_sequence'])
            curr_seat.write({
                'seat': seat['seat'],
                'seat_code': seat['seat_code']
            })
            ## ADD BEHAVIOR 24 feb 2023 IVAN
            if seat.get('behaviors'):
                if seat['behaviors'].get('Train'):
                    curr_seat.passenger_id.customer_id.add_behavior('train', seat['behaviors']['Train'])