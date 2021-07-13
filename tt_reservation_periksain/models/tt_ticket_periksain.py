from odoo import api, fields, models, _
from ...tools import variables


class TtTicketPeriksain(models.Model):
    _name = 'tt.ticket.periksain'
    _description = 'Ticket Periksain'

    provider_id = fields.Many2one('tt.provider.periksain', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.periksain', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number
        }
        return res
