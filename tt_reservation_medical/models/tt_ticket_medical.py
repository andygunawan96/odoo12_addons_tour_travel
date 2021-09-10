from odoo import api, fields, models, _
from ...tools import variables


class TtTicketmedical(models.Model):
    _name = 'tt.ticket.medical'
    _description = 'Ticket medical'

    provider_id = fields.Many2one('tt.provider.medical', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.medical', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number
        }
        return res
