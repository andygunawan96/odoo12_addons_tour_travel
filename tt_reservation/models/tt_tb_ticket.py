from odoo import api, fields, models, _


class TtTbTicket(models.Model):
    _name = 'tt.tb.ticket'

    passenger_id = fields.Many2one('tt.customer', 'Passenger')
    seat_number = fields.Char('Seat Number')
    ticket_number = fields.Char('Ticket Number')
    tb_provider_id = fields.Many2one('tt.tb.provider', 'Provider')
