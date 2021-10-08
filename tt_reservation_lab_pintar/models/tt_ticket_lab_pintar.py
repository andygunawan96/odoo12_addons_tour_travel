from odoo import api, fields, models, _
from ...tools import variables


class TtTicketLabPintar(models.Model):
    _name = 'tt.ticket.lab.pintar'
    _description = 'Ticket Lab Pintar'

    provider_id = fields.Many2one('tt.provider.lab.pintar', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.lab.pintar', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number
        }
        return res
