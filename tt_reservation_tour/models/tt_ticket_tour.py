from odoo import api, fields, models, _
from ...tools import variables

class TtTicketTour(models.Model):
    _name = 'tt.ticket.tour'
    _description = 'Ticket Tour'

    provider_id = fields.Many2one('tt.provider.tour', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.tour', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')
    tour_room_id = fields.Many2one('tt.master.tour.rooms', 'Room')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'tour_room_id': self.tour_room_id.name,
            'sequence': self.passenger_id and self.passenger_id.sequence or '',
            'passenger_number': int(self.passenger_id.sequence) if self.passenger_id else ''
        }
        return res
