from odoo import api, fields, models, _
from ...tools import variables

class TtTicketInsurance(models.Model):
    _name = 'tt.ticket.insurance'
    _description = 'Ticket Insurance'

    provider_id = fields.Many2one('tt.provider.insurance', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.insurance', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE, 'Pax Type')
    ticket_number = fields.Char('Ticket Number', default='')
    ticket_url = fields.Char('Ticket URL', default='')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number,
            'ticket_url': self.ticket_url,
            'sequence': self.passenger_id and self.passenger_id.sequence or '',
            'passenger_number': int(self.passenger_id.sequence) if self.passenger_id else '',
        }
        return res
