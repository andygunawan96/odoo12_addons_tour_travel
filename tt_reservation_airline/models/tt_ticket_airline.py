from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TtTicketAirline(models.Model):
    _name = 'tt.ticket.airline'

    provider_id = fields.Many2one('tt.provider.airline', 'Provider')
    passenger_id = fields.Many2one('tt.customer', 'Passenger')
    ticket_number = fields.Char('Ticket Number')