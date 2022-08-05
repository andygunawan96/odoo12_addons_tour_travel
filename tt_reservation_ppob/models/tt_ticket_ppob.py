from odoo import api, fields, models, _
from ...tools import variables


class TtTicketPPOB(models.Model):
    _name = 'tt.ticket.ppob'
    _description = 'Ticket PPOB'

    provider_id = fields.Many2one('tt.provider.ppob', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.ppob', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'sequence': self.passenger_id and self.passenger_id.sequence or '',
            'passenger_number': int(self.passenger_id.sequence) if self.passenger_id else ''
        }
        return res
