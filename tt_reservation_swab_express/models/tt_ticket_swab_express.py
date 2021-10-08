from odoo import api, fields, models, _
from ...tools import variables


class TtTicketSwabExpress(models.Model):
    _name = 'tt.ticket.swab.express'
    _description = 'Ticket Swab Express'

    provider_id = fields.Many2one('tt.provider.swab.express', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.swab.express', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number
        }
        return res
