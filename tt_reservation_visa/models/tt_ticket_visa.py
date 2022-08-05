from odoo import api, fields, models, _
from ...tools import variables

class TtTicketVisa(models.Model):
    _name = 'tt.ticket.visa'
    _description = 'Ticket Visa'

    provider_id = fields.Many2one('tt.provider.visa', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.visa', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'sequence': self.passenger_id and self.passenger_id.sequence or '',
            'passenger_number': int(self.passenger_id.sequence) if self.passenger_id else ''
        }
        return res
