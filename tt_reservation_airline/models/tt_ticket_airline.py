from odoo import api, fields, models, _
from ...tools import variables

class TtTicketAirline(models.Model):
    _name = 'tt.ticket.airline'
    _description = 'Ticket Airline'

    provider_id = fields.Many2one('tt.provider.airline', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.airline', 'Passenger')
    loyalty_program_id = fields.Many2one('tt.loyalty.program', 'Loyalty Program', compute='_compute_loyalty_program', store=True)
    pax_type  = fields.Selection(variables.PAX_TYPE,'Pax Type')
    ticket_number = fields.Char('Ticket Number', default='')
    ff_number = fields.Char('Frequent Flyer Number', default='')
    ff_code = fields.Char('Frequent Flyer Code', default='')

    @api.depends('ff_number', 'passenger_id', 'passenger_id.frequent_flyer_ids')
    def _compute_loyalty_program(self):
        for rec in self:
            if not rec.passenger_id:
                continue

            for ff in rec.passenger_id.frequent_flyer_ids:
                if ff.ff_number == rec.ff_number:
                    rec.update({
                        'loyalty_program_id': ff.loyalty_program_id.id,
                        'ff_code': ff.ff_code
                    })
                    break

    def to_dict(self):
        fees = [fee.to_dict() for fee in self.passenger_id.fee_ids]
        res = {
            'passenger': self.passenger_id and self.passenger_id.name or '',
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number and self.ticket_number or '',
            'ff_number': self.ff_number and self.ff_number or '',
            'ff_code': self.ff_code and self.ff_code or '',
            'ff_name': self.loyalty_program_id and self.loyalty_program_id.name or '',
            'fees': fees,
            'sequence': self.passenger_id and self.passenger_id.sequence or '',
            'passenger_number': self.passenger_id.sequence if self.passenger_id else '',
        }
        return res
