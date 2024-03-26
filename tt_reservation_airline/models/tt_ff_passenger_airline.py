from odoo import api, fields, models, _
from ...tools import variables

class TtFfPassengerAirline(models.Model):
    _name = 'tt.ff.passenger.airline'
    _description = 'FF Passenger Airline'

    name = fields.Char('Name', default='')
    first_name = fields.Char('First Name', default='')
    last_name = fields.Char('Last Name', default='')
    passenger_id = fields.Many2one('tt.reservation.passenger.airline', 'Passenger')
    loyalty_program_id = fields.Many2one('tt.loyalty.program', 'Loyalty Program')
    provider_id = fields.Many2one('tt.provider.airline', 'Provider')
    provider_sequence = fields.Integer('Provider Sequence', related='provider_id.sequence')
    ff_number = fields.Char('Frequent Flyer Number', default='')
    ff_code = fields.Char('Frequent Flyer Code', default='')
    schedule_id = fields.Char('Schedule ID', default='')

    def to_dict(self):
        res = {
            'name': self.name and self.name or '',
            'first_name': self.first_name and self.first_name or '',
            'last_name': self.last_name and self.last_name or '',
            'provider_sequence': self.provider_sequence,
            'ff_code': self.ff_code and self.ff_code or '',
            'ff_name': self.loyalty_program_id and self.loyalty_program_id.name or '',
            'ff_number': self.ff_number and self.ff_number or '',
            'schedule_id': self.schedule_id and self.schedule_id or '',
        }
        return res

class TtReservationPassengerAirlineInherit(models.Model):
    _inherit = 'tt.reservation.passenger.airline'
    _description = 'Reservation Passenger Airline'

    frequent_flyer_ids = fields.One2many('tt.ff.passenger.airline', 'passenger_id', 'Frequent Flyers')

    def to_dict(self):
        res = super(TtReservationPassengerAirlineInherit, self).to_dict()
        frequent_flyers = [rec.to_dict() for rec in self.frequent_flyer_ids]
        res.update({
            'frequent_flyers': frequent_flyers
        })
        return res
