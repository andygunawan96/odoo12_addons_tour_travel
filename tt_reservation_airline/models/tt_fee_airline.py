from odoo import api,models,fields
import json
from datetime import datetime, timedelta
import logging, traceback

_logger = logging.getLogger(__name__)

class TtSsrAirline(models.Model):
    _name = 'tt.fee.airline'
    _description = 'Fee Airline Model'

    name = fields.Char("Name")
    type = fields.Char("Type")
    code = fields.Char("Code")
    value = fields.Char("Value")
    category = fields.Char("Category")
    category_icon = fields.Char("Category Icon", compute="_compute_category_icon",store=True)
    description = fields.Text("Description")
    amount = fields.Monetary("Amount")
    currency_id = fields.Many2one("res.currency","Currency",default=lambda self:self.env.user.company_id.currency_id)
    passenger_id = fields.Many2one("tt.reservation.passenger.airline","Passenger")
    pnr = fields.Char('PNR', default='')
    # May 18, 2020 - SAM
    provider_id = fields.Many2one('tt.provider.airline', 'Provider', default=None)
    journey_code = fields.Char('Journey Code', default='')
    # END
    ticket_number = fields.Char("Ticket Number", default='')

    @api.depends('category')
    def _compute_category_icon(self):
        for rec in self:
            try:
                rec.category_icon = self.env['tt.ssr.category'].search([('key','=',rec.category)],limit=1).icon
            except:
                rec.category_icon = 'fa fa-suitcase'

    def convert_json_to_str(self, json_data):
        try:
            final_str = ''
            if json_data:
                # temp_dict = json.loads(json_data)
                # for key, val in temp_dict.items():
                #     final_str += '%s: %s\n' % (key, val)
                data_list = json.loads(json_data)
                final_str = ', '.join(data_list)
        except:
            final_str = json_data
        return final_str

    def to_dict(self):
        return {
            'fee_name': self.name,
            'fee_type': self.type,
            'fee_code': self.code,
            'fee_value': self.value,
            'ticket_number': self.ticket_number and self.ticket_number or '',
            'fee_category': self.category,
            'description': json.loads(self.description),
            'description_text': self.convert_json_to_str(self.description),
            'amount': self.amount,
            'currency': self.currency_id.name,
            'journey_code': self.journey_code and self.journey_code or '',
            'pnr': self.provider_id and self.provider_id.pnr or '',
            'passenger_number': self.passenger_id.sequence if self.passenger_id else '',
        }


class TtProviderAirlineInherit(models.Model):
    _inherit = 'tt.provider.airline'
    _description = 'Provider Airline Model Inherit'

    # May 18, 2020 - SAM
    fee_ids = fields.One2many('tt.fee.airline', 'provider_id', 'Fees')
    # END

    def to_dict(self):
        result = super(TtProviderAirlineInherit, self).to_dict()
        fees = [rec.to_dict() for rec in self.fee_ids]
        result.update({
            'fees': fees,
        })
        return result
