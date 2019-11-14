from odoo import api, fields, models, _
from ...tools import variables

class TtTicketTrain(models.Model):
    _name = 'tt.ticket.train'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider.train', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.train', 'Passenger')
    pax_type  = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number')


    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number,
            'passenger_sequence': self.passenger_id.sequence
        }
        return res