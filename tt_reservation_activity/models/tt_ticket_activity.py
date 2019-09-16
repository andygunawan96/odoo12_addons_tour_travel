from odoo import api, fields, models, _
from ...tools import variables

class TtTicketActivity(models.Model):
    _name = 'tt.ticket.activity'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider.activity', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.activity', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('SKU ID')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number
        }
        return res