from odoo import api, fields, models, _
from ...tools import variables

class TtTicketInsurance(models.Model):
    _name = 'tt.ticket.insurance'
    _description = 'Ticket Insurance'

    provider_id = fields.Many2one('tt.provider.insurance', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.insurance', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE, 'Pax Type')
    ticket_number = fields.Char('Ticket Number', default='')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number
        }
        return res
