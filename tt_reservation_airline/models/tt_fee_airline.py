from odoo import api,models,fields
import json
from datetime import datetime, timedelta
import logging, traceback

_logger = logging.getLogger(__name__)

class TtSsrAirline(models.Model):
    _name = 'tt.fee.airline'
    _description = 'Fee Airline Model'
    _order = 'departure_date_utc'

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
    departure_date_utc = fields.Datetime('Departure Date (UTC)', compute='_compute_departure_date_utc', store=True, readonly=1)
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

    @api.depends('journey_code')
    def _compute_departure_date_utc(self):
        for rec in self:
            try:
                if rec.journey_code:
                    journey_code = rec.journey_code.split(',')
                    departure_date = journey_code[3]
                    dept_time_obj = None
                    try:
                        dept_time_obj = datetime.strptime(departure_date, '%Y-%m-%d %H:%M:%S')
                    except:
                        departure_date = None
                    origin_obj = self.env['tt.destinations'].search([('code','=',journey_code[2]),('provider_type_id.code','=','airline')], limit=1)
                    # origin_obj = journey_code[2]
                    if not origin_obj or not dept_time_obj:
                        rec.departure_date_utc = departure_date
                        continue

                    utc_time = origin_obj.timezone_hour
                    rec.departure_date_utc = dept_time_obj - timedelta(hours=utc_time)
            except Exception as e:
                _logger.error("%s, %s" % (str(e), traceback.format_exc()))


class TtProviderAirlineInherit(models.Model):
    _inherit = 'tt.provider.airline'
    _description = 'Provider Airline Model Inherit'

    # May 18, 2020 - SAM
    fee_ids = fields.One2many('tt.fee.airline', 'provider_id', 'Fees')
    # END

    def to_dict(self):
        result = super().to_dict()
        fees = [rec.to_dict() for rec in self.fee_ids]
        result.update({
            'fees': fees,
        })
        return result
