from odoo import api, fields, models, _
from ...tools import variables

class TtTicketAirline(models.Model):
    _name = 'tt.ticket.airline'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider.airline', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.airline', 'Passenger')
    pax_type  = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number', default='')
    ff_number = fields.Char('Frequent Flyer Number', default='')
    ff_code = fields.Char('Frequent Flyer Code', default='')

    def to_dict(self):
        fees = [fee.to_dict() for fee in self.passenger_id.fee_ids]
        res = {
            'passenger': self.passenger_id and self.passenger_id.name or '',
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number and self.ticket_number or '',
            'ff_number': self.ff_number and self.ff_number or '',
            'ff_code': self.ff_code and self.ff_code or '',
            'fees': fees,
        }
        return res
