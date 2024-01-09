from odoo import api, fields, models, _
from ...tools import variables
import json


class TtTicketAirline(models.Model):
    _name = 'tt.ticket.airline'
    _description = 'Ticket Airline'

    provider_id = fields.Many2one('tt.provider.airline', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.airline', 'Passenger')
    loyalty_program_id = fields.Many2one('tt.loyalty.program', 'Loyalty Program', compute='_compute_loyalty_program', store=True)
    pax_type = fields.Selection(variables.PAX_TYPE, 'Pax Type')
    ticket_number = fields.Char('Ticket Number', default='')
    ff_number = fields.Char('Frequent Flyer Number', default='')
    ff_code = fields.Char('Frequent Flyer Code', default='')
    title = fields.Char('Title', default='')
    first_name = fields.Char('First Name', default='')
    last_name = fields.Char('Last Name', default='')
    birth_date = fields.Char('Birth Date', default='')
    identity_type = fields.Char('Identity Type', default='')
    identity_number = fields.Char('Identity Number', default='')
    identity_expdate = fields.Char('Identity Expdate', default='')
    identity_country_of_issued_code = fields.Char('Identity Country of Issued Code', default='')
    ticket_number_list = fields.Char('Ticket Number List', default='')
    riz_text = fields.Char('RIZ Text', default='')

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
        ticket_number_list = []
        try:
            if self.ticket_number_list:
                load_tickets = [rec.strip() for rec in self.ticket_number_list.split(';')]
                ticket_number_list = load_tickets
        except:
            pass
        res = {
            'ticket_id': 'TKT_%s' % self.id,
            'passenger': self.passenger_id and self.passenger_id.name or '',
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number and self.ticket_number or '',
            'ff_number': self.ff_number and self.ff_number or '',
            'ff_code': self.ff_code and self.ff_code or '',
            'ff_name': self.loyalty_program_id and self.loyalty_program_id.name or '',
            'fees': fees,
            'sequence': self.passenger_id and self.passenger_id.sequence or '',
            'passenger_number': int(self.passenger_id.sequence) if self.passenger_id else '',
            'title': self.title if self.title else '',
            'first_name': self.first_name if self.first_name else '',
            'last_name': self.last_name if self.last_name else '',
            'birth_date': self.birth_date if self.birth_date else '',
            'identity_type': self.identity_type if self.identity_type else '',
            'identity_number': self.identity_number if self.identity_number else '',
            'identity_expdate': self.identity_expdate if self.identity_expdate else '',
            'identity_country_of_issued_code': self.identity_country_of_issued_code if self.identity_country_of_issued_code else '',
            'ticket_number_list': ticket_number_list,
            'riz_text': self.riz_text if self.riz_text else '',
        }
        return res
