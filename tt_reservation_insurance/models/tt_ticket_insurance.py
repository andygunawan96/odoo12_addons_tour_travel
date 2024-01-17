from odoo import api, fields, models, _
from ...tools import variables

class TtTicketInsurance(models.Model):
    _name = 'tt.ticket.insurance'
    _description = 'Ticket Insurance'

    provider_id = fields.Many2one('tt.provider.insurance', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.passenger.insurance', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE, 'Pax Type')
    ticket_number = fields.Char('Ticket Number', default='')
    ticket_url = fields.Char('Ticket URL', default='')
    policy_number = fields.Char('Policy Number', default='')

    printout_quotation_ids = fields.Many2many('tt.upload.center', 'quotation_insurance_attachment_rel', 'quotation_ticket_id','attachment_id', string='Attachments')

    def to_dict(self):
        res = {
            'passenger': self.passenger_id.name,
            'pax_type': self.pax_type,
            'ticket_number': self.ticket_number,
            'ticket_url': self.ticket_url,
            'printout_quotation': [rec.url for rec in self.printout_quotation_ids] if self.printout_quotation_ids else [],
            'sequence': self.passenger_id and self.passenger_id.sequence or '',
            'passenger_number': int(self.passenger_id.sequence) if self.passenger_id else '',
        }
        return res
