from odoo import api, fields, models, _
from ...tools import variables


class TtTicketphc(models.Model):
    _name = 'tt.ticket.phc'
    _description = 'Ticket phc'

    provider_id = fields.Many2one('tt.provider.phc', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.phc', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number
        }
        return res
