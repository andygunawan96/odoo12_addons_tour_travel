from odoo import api, fields, models, _
from ...tools import variables


class TtTicketSentraMedika(models.Model):
    _name = 'tt.ticket.sentramedika'
    _description = 'Ticket Sentra Medika'

    provider_id = fields.Many2one('tt.provider.sentramedika', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.sentramedika', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number
        }
        return res
