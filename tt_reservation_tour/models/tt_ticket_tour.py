from odoo import api, fields, models, _
from ...tools import variables

class TtTicketTour(models.Model):
    _name = 'tt.ticket.tour'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider.tour', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.tour', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number
        }
        return res
