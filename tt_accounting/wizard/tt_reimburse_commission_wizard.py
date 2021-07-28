from ...tools.repricing_tools import RepricingTools
from odoo import fields, models, api, _
from ...tools import util,variables,ERR
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import pytz
import logging,traceback

_logger = logging.getLogger(__name__)


class ReimburseCommissionWizard(models.TransientModel):
    _name = 'tt.reimburse.commission.wizard'

    period = fields.Selection([('today', 'Today'), ('yesterday', 'Yesterday'),
                               ('1', 'This month'), ('2', 'A month ago'), ('3', 'Two month ago'),
                               ('custom', 'Custom')], 'Period', default='today', required=True)

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)

    def get_provider_domain(self):
        return [('provider_type_id', '=', self.provider_type_id.id)]

    provider_id = fields.Many2one('tt.provider', 'Provider', required=True, domain=get_provider_domain)
    rac_mode = fields.Selection([('fare', 'Fare'), ('tax', 'Tax'), ('fare_tax', 'Fare + Tax')], 'Commission Mode', default='fare', required=True)
    rac_amount = fields.Float('Commission Amount (Percentage %)', default=0.0)

    @api.onchange('provider_type_id')
    def _onchange_domain_provider(self):
        self.provider_id = False
        return {'domain': {
            'provider_id': self.get_provider_domain()
        }}

    @api.onchange('period')
    def _onchage_period(self):
        if self.period in ('today', 'custom'):
            self.date_from = fields.Date.context_today(self)
            self.date_to = fields.Date.context_today(self)
        elif self.period == 'yesterday':
            self.date_from = (fields.Date.from_string(fields.Date.context_today(self)) - timedelta(days=1)).strftime(
                '%Y-%m-%d')
            self.date_to = self.date_from
        elif self.period == '1':
            self.date_from = datetime.now().strftime('%Y-%m-01')
            self.date_to = fields.Date.context_today(self)
        elif self.period == '2':
            self.date_from = (datetime.today() - relativedelta(months=+1)).strftime('%Y-%m-01')
            self.date_to = (self.date_from + relativedelta(months=+1, days=-1)).strftime('%Y-%m-%d')
        elif self.period == '3':
            self.date_from = (datetime.today() - relativedelta(months=+2)).strftime('%Y-%m-01')
            self.date_to = (self.date_from + relativedelta(months=+1, days=-1)).strftime('%Y-%m-%d')

    def convert_timezone(self, date_from_target, date_to_target):
        user_tz = pytz.timezone('Asia/Jakarta')
        if not date_from_target:
            date_from_target = fields.Date.context_today(self)
        if not date_to_target:
            date_to_target = fields.Date.context_today(self)
        date_from_utc = date_from_target
        date_from_utc = user_tz.localize(fields.Datetime.from_string(date_from_utc))
        date_from = date_from_utc.astimezone(pytz.timezone('UTC'))
        date_to_utc = '%s %s' % (date_to_target, '23:59:59')
        date_to_utc = user_tz.localize(fields.Datetime.from_string(date_to_utc))
        date_to = date_to_utc.astimezone(pytz.timezone('UTC'))

        return {
            'date_from': date_from,
            'date_to': date_to
        }

    def calculate_pricing(self, provider_type_code, pricing_values):
        repr_obj = RepricingTools(provider_type_code)
        res = repr_obj.get_service_charge_pricing(**pricing_values)
        return res

    def reimburse_commission(self):
        try:
            if self.rac_amount >= 100 or self.rac_amount <= 0:
                raise UserError(_('Commission Amount must be between 1-99%'))
            table = 'tt.provider.%s' % self.provider_type_id.code
            date_range_dict = self.convert_timezone(self.date_from, self.date_to)
            date_from = date_range_dict['date_from']
            date_to = date_range_dict['date_to']
            resv_provider_list = self.env[table].search([('provider_id', '=', self.provider_id.id), ('state', '=', 'issued'),
                                                         ('issued_date', '>=', date_from), ('issued_date', '<=', date_to)])
            for rec in resv_provider_list:
                double_check = self.env['tt.reimburse.commission'].search([('res_model', '=', rec._name),
                                                                           ('res_id', '=', rec.id), ('state', 'in', ['draft', 'approved'])])
                if double_check:
                    continue
                total_nta_amount = 0
                nta_amount = {
                    'ADT': 0,
                    'CHD': 0,
                    'INF': 0,
                    'YCD': 0,
                }
                if self.rac_mode == 'fare_tax':
                    filter_list = ['FARE', 'TAX']
                elif self.rac_mode == 'tax':
                    filter_list = ['TAX']
                else:
                    filter_list = ['FARE']
                for rec2 in rec.cost_service_charge_ids:
                    if rec2.charge_type in filter_list:
                        total_nta_amount += rec2.total
                        nta_amount[rec2.pax_type] += rec2.total
                adt_count = 0
                chd_count = 0
                inf_count = 0
                ycd_count = 0
                if self.provider_type_id.code in ['airline', 'train', 'tour', 'activity', 'visa', 'passport', 'phc', 'periksain']:
                    for psg in rec.ticket_ids:
                        if psg.pax_type == 'INF':
                            inf_count += 1
                        elif psg.pax_type == 'CHD':
                            chd_count += 1
                        elif psg.pax_type == 'YCD':
                            ycd_count += 1
                        else:
                            adt_count += 1
                else:
                    adt_count += rec.booking_id.adult
                    chd_count += rec.booking_id.child
                    inf_count += rec.booking_id.infant

                adt_scs_list = []
                chd_scs_list = []
                inf_scs_list = []
                ycd_scs_list = []
                rac_amount_total = 0
                user_info = self.env['tt.agent'].sudo().get_agent_level(rec.booking_id.agent_id.id)
                if adt_count > 0:
                    rac_amount_total += (self.rac_amount / 100) * nta_amount['ADT']
                    adt_scs_list = self.calculate_pricing(rec.provider_id.provider_type_id.code, {
                        'fare_amount': 0,
                        'tax_amount': 0,
                        'roc_amount': 0,
                        'rac_amount': (((self.rac_amount / 100) * nta_amount['ADT']) / adt_count) * -1,
                        'currency': 'IDR',
                        'provider': rec.provider_id.code,
                        'origin': '',
                        'destination': '',
                        'carrier_code': '',
                        'class_of_service': '',
                        'route_count': 1,
                        'segment_count': 1,
                        'pax_count': adt_count,
                        'pax_type': 'ADT',
                        'agent_type_code': rec.booking_id.agent_type_id.code,
                        'agent_id': rec.booking_id.agent_id.id,
                        'user_info': user_info,
                        'is_pricing': False,
                        'is_commission': True,
                        'is_retrieved': False,
                        'pricing_date': '',
                        'show_upline_commission': True
                    })
                if chd_count > 0:
                    rac_amount_total += (self.rac_amount / 100) * nta_amount['CHD']
                    chd_scs_list = self.calculate_pricing(rec.provider_id.provider_type_id.code, {
                        'fare_amount': 0,
                        'tax_amount': 0,
                        'roc_amount': 0,
                        'rac_amount': (((self.rac_amount / 100) * nta_amount['CHD']) / chd_count) * -1,
                        'currency': 'IDR',
                        'provider': rec.provider_id.code,
                        'origin': '',
                        'destination': '',
                        'carrier_code': '',
                        'class_of_service': '',
                        'route_count': 1,
                        'segment_count': 1,
                        'pax_count': chd_count,
                        'pax_type': 'CHD',
                        'agent_type_code': rec.booking_id.agent_type_id.code,
                        'agent_id': rec.booking_id.agent_id.id,
                        'user_info': user_info,
                        'is_pricing': False,
                        'is_commission': True,
                        'is_retrieved': False,
                        'pricing_date': '',
                        'show_upline_commission': True
                    })
                if inf_count > 0:
                    rac_amount_total += (self.rac_amount / 100) * nta_amount['INF']
                    inf_scs_list = self.calculate_pricing(rec.provider_id.provider_type_id.code, {
                        'fare_amount': 0,
                        'tax_amount': 0,
                        'roc_amount': 0,
                        'rac_amount': (((self.rac_amount / 100) * nta_amount['INF']) / inf_count) * -1,
                        'currency': 'IDR',
                        'provider': rec.provider_id.code,
                        'origin': '',
                        'destination': '',
                        'carrier_code': '',
                        'class_of_service': '',
                        'route_count': 1,
                        'segment_count': 1,
                        'pax_count': inf_count,
                        'pax_type': 'INF',
                        'agent_type_code': rec.booking_id.agent_type_id.code,
                        'agent_id': rec.booking_id.agent_id.id,
                        'user_info': user_info,
                        'is_pricing': False,
                        'is_commission': True,
                        'is_retrieved': False,
                        'pricing_date': '',
                        'show_upline_commission': True
                    })
                if ycd_count > 0:
                    rac_amount_total += (self.rac_amount / 100) * nta_amount['YCD']
                    ycd_scs_list = self.calculate_pricing(rec.provider_id.provider_type_id.code, {
                        'fare_amount': 0,
                        'tax_amount': 0,
                        'roc_amount': 0,
                        'rac_amount': (((self.rac_amount / 100) * nta_amount['YCD']) / ycd_count) * -1,
                        'currency': 'IDR',
                        'provider': rec.provider_id.code,
                        'origin': '',
                        'destination': '',
                        'carrier_code': '',
                        'class_of_service': '',
                        'route_count': 1,
                        'segment_count': 1,
                        'pax_count': ycd_count,
                        'pax_type': 'YCD',
                        'agent_type_code': rec.booking_id.agent_type_id.code,
                        'agent_id': rec.booking_id.agent_id.id,
                        'user_info': user_info,
                        'is_pricing': False,
                        'is_commission': True,
                        'is_retrieved': False,
                        'pricing_date': '',
                        'show_upline_commission': True
                    })
                commission_list = adt_scs_list + chd_scs_list + inf_scs_list + ycd_scs_list
                if commission_list:
                    reimburse_obj = self.env['tt.reimburse.commission'].create({
                        'res_model': rec._name,
                        'res_id': rec.id,
                        'reservation_ref': rec.booking_id.name,
                        'provider_pnr': rec.pnr,
                        'provider_issued_date': rec.issued_date,
                        'rac_mode': self.rac_mode,
                        'base_price': total_nta_amount,
                        'rac_amount': self.rac_amount,
                        'currency_id': rec.currency_id.id,
                        'rac_amount_num': rac_amount_total,
                        'state': 'draft'
                    })
                    for comm in commission_list:
                        temp_comm = comm
                        currency_obj = self.env['res.currency'].search([('name', '=', comm['currency'])])
                        temp_comm.update({
                            'reimburse_id': reimburse_obj.id,
                            'currency_id': currency_obj and currency_obj[0].id or False
                        })
                        self.env['tt.reimburse.commission.service.charge'].create(temp_comm)
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise UserError(_('Error line : ' + str(e)))
