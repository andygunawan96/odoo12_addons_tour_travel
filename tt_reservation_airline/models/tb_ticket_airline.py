from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TransportBookingTicket(models.Model):
    _name = 'tt.tb.ticket.airline'

    provider_id = fields.Many2one('tt.tb.provider.airline', 'Provider')
    passenger_id = fields.Many2one('tt.customer', 'Passenger')
    ticket_number = fields.Char('Ticket Number')