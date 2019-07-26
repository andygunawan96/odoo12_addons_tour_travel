from odoo import api, fields, models, _
from ...tools import variables

class TtTicketAirline(models.Model):
    _name = 'tt.ticket.airline'

    provider_id = fields.Many2one('tt.provider.airline', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.airline', 'Passenger')
    pax_type  = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number')

    def to_dict(self):
        res = {}
        return res