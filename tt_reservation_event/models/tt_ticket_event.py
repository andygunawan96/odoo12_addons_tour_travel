from odoo import api, fields, models, _
from ...tools import variables

class TtTicketEvent(models.Model):
    _name = 'tt.ticket.event'
    _description = 'Orbis Event Model'

    provider_id = fields.Many2one('tt.provider.event', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.event', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE, 'Pax Type')
    ticket_number = fields.Char('SKU ID')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number,
            'sequence': self.passenger_id and self.passenger_id.sequence or '',
            'passenger_number': int(self.passenger_id.sequence) if self.passenger_id else ''
        }
        return res