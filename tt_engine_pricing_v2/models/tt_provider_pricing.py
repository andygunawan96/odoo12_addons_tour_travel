from odoo import models, fields, api, _
from ...tools import variables
from ...tools.api import Response
import traceback, logging
from datetime import datetime, timedelta
import json

_logger = logging.getLogger(__name__)

ACCESS_TYPE = [
    ('all', 'ALL'),
    ('allow', 'Allowed'),
    ('restrict', 'Restricted'),
]

STATE = [
    ('enable', 'Enable'),
    ('disable', 'Disable'),
]

FORMAT_DATETIME = '%Y-%m-%d %H:%M:%S'
EXPIRED_SECONDS = 300


class ProviderPricing(models.Model):
    _name = 'tt.provider.pricing'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Provider Pricing'

    name = fields.Char('Name', compute='_compute_name', store=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)

    provider_name = fields.Char('Provider Name', compute='_compute_provider_name', store=True)
    provider_access_type = fields.Selection(ACCESS_TYPE, 'Provider Access Type', default='allow', required=True)
    provider_ids = fields.Many2many('tt.provider', 'tt_provider_pricing_provider_rel', 'pricing_id', 'provider_id',
                                    string='Providers', domain='[("provider_type_id", "=", provider_type_id)]')

    carrier_name = fields.Char('Carrier Name', compute='_compute_carrier_name', store=True)
    carrier_access_type = fields.Selection(ACCESS_TYPE, 'Carrier Access Type', default='all', required=True)
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_provider_pricing_carrier_rel', 'pricing_id', 'carrier_id',
                                   string='Carriers', domain='[("provider_type_id", "=", provider_type_id)]')

    line_ids = fields.One2many('tt.provider.pricing.line', 'pricing_id', string='Rules', context={'active_test': False}, copy=True)

    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)

    @api.depends('provider_type_id', 'provider_name', 'carrier_name')
    def _compute_name(self):
        for rec in self:
            name_list = []
            if rec.provider_type_id:
                name_list.append(rec.provider_type_id.name)
            if rec.carrier_name:
                name_list.append('[%s]' % rec.carrier_name)
            if rec.provider_name:
                name_list.append('[%s]' % rec.provider_name)

            name = ' '.join(name_list)
            rec.name = name

    @api.depends('provider_access_type', 'provider_ids')
    def _compute_provider_name(self):
        for rec in self:
            name_list = []
            provider_name = 'In All Providers'
            if rec.provider_access_type != 'all':
                for provider in rec.provider_ids:
                    name_list.append('%s' % provider.name)
                provider_name = '%s in Provider %s' % (rec.provider_access_type.title(), ','.join(name_list))
            rec.provider_name = provider_name

    @api.depends('carrier_access_type', 'carrier_ids')
    def _compute_carrier_name(self):
        for rec in self:
            name_list = []
            carrier_name = 'for All Carriers'
            if rec.carrier_access_type != 'all':
                for carrier in rec.carrier_ids:
                    name_list.append('%s (%s)' % (carrier.name, carrier.code))
                carrier_name = '%s for Carrier %s' % (rec.carrier_access_type.title(), ','.join(name_list))
            rec.carrier_name = carrier_name

    def test_get_data(self):
        res = self.get_data()
        msg = 'Get Data : %s' % json.dumps(res)
        print(msg)
        _logger.info(msg)
        return True

    def get_data(self):
        res = {
            'id': self.id,
            'name': self.name if self.name else '',
            'provider_type_code': self.provider_type_id.code if self.provider_type_id else '',
            'provider': {
                'access_type': self.provider_access_type,
                'provider_code_list': [rec.code for rec in self.provider_ids]
            },
            'carrier': {
                'access_type': self.carrier_access_type,
                'carrier_code_list': [rec.code for rec in self.carrier_ids]
            },
            'rule_list': [rec.get_data() for rec in self.line_ids],
            'state': self.state
        }
        return res

    def get_provider_pricing_api(self):
        try:
            objs = self.env['tt.provider.pricing'].sudo().search([])
            provider_pricing_data = {}
            date_now = datetime.now().strftime(FORMAT_DATETIME)
            expired_date = datetime.now() + timedelta(seconds=EXPIRED_SECONDS)
            expired_date = expired_date.strftime(FORMAT_DATETIME)
            for obj in objs:
                if not obj.active or obj.state == 'disable':
                    continue

                vals = obj.get_data()
                provider_type_code = vals['provider_type_code']
                if provider_type_code not in provider_pricing_data:
                    provider_pricing_data[provider_type_code] = {
                        'provider_pricing_list': [],
                        'create_date': date_now,
                        'expired_date': expired_date,
                    }
                provider_pricing_data[provider_type_code]['provider_pricing_list'].append(vals)

            payload = {
                'provider_pricing_data': provider_pricing_data
            }
        except Exception as e:
            _logger.error('Error Get Provider Pricing Data, %s' % traceback.format_exc())
            payload = {}
        return payload


class ProviderPricingLine(models.Model):
    _name = 'tt.provider.pricing.line'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Provider Pricing Line'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    pricing_id = fields.Many2one('tt.provider.pricing', 'Provider Pricing', readonly=1, ondelete='cascade')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', related='pricing_id.provider_type_id')
    set_expiration_date = fields.Boolean('Set Expiration Date', default=False)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')

    origin_name = fields.Char('Origin Name')
    origin_access_type = fields.Selection(ACCESS_TYPE, 'Origin Access Type', default='all', required=True)
    origin_ids = fields.Many2many('tt.destinations', 'tt_provider_pricing_destinations_origin_rel',
                                  'pricing_line_id', 'destination_id', string='Origin', domain='[("provider_type_id", "=", provider_type_id)]')
    origin_city_ids = fields.Many2many('res.city', 'tt_provider_pricing_city_origin_rel',
                                       'pricing_line_id', 'city_id', string='Origin Cities')
    origin_country_ids = fields.Many2many('res.country', 'tt_provider_pricing_country_origin_rel',
                                          'pricing_line_id', 'country_id', string='Origin Countries')

    destination_name = fields.Char('Destination Name')
    destination_access_type = fields.Selection(ACCESS_TYPE, 'Destination Access Type', default='all', required=True)
    destination_ids = fields.Many2many('tt.destinations', 'tt_provider_pricing_destinations_destination_rel',
                                       'pricing_line_id', 'destination_id', string='Destination', domain='[("provider_type_id", "=", provider_type_id)]')
    destination_city_ids = fields.Many2many('res.city', 'tt_provider_pricing_city_destination_rel',
                                            'pricing_line_id', 'city_id', string='Destination Cities')
    destination_country_ids = fields.Many2many('res.country', 'tt_provider_pricing_country_destination_rel',
                                               'pricing_line_id', 'country_id', string='Destination Countries')

    class_of_service_name = fields.Char('Class of Service Name')
    class_of_service_access_type = fields.Selection(ACCESS_TYPE, 'Class of Service Access Type', default='all', required=True)
    class_of_service_list = fields.Char('Class of Service List', help='Use comma (,) for separate the values')

    charge_code_name = fields.Char('Charge Code Name')
    charge_code_access_type = fields.Selection(ACCESS_TYPE, 'Charge Code Access Type', default='all', required=True)
    charge_code_list = fields.Char('Charge Code List', help='Use comma (,) for separate the values')

    less_percentage = fields.Float('Vendor Less (%)', default=0)
    less_infant = fields.Boolean('Apply less to Infant', default=False)

    tkt_nta_fare_percentage = fields.Float('Fare (%)', default=0)
    tkt_nta_fare_amount = fields.Float('Fare Amount', default=0)
    tkt_nta_tax_percentage = fields.Float('Tax (%)', default=0)
    tkt_nta_tax_amount = fields.Float('Tax Amount', default=0)
    tkt_nta_total_percentage = fields.Float('Total (%)', default=0)
    tkt_nta_total_amount = fields.Float('Total Amount', default=0)
    tkt_nta_upsell_percentage = fields.Float('Upsell (%)', default=0)
    tkt_nta_upsell_minimum = fields.Float('Upsell Minimum Amount', default=0)
    tkt_nta_upsell_amount = fields.Float('Upsell Amount', default=0)
    tkt_nta_upsell_route = fields.Boolean('Upsell per Route', default=False)
    tkt_nta_upsell_segment = fields.Boolean('Upsell per Segment', default=False)
    # tkt_nta_upsell_pax = fields.Boolean('Upsell per Pax', default=False)
    tkt_nta_fare_infant = fields.Boolean('Apply Fare Pricing to Infant', default=False)
    tkt_nta_tax_infant = fields.Boolean('Apply Tax Pricing to Infant', default=False)
    tkt_nta_total_infant = fields.Boolean('Apply Total Pricing to Infant', default=True)
    tkt_nta_upsell_percentage_infant = fields.Boolean('Apply Upsell Percentage to Infant', default=False)
    tkt_nta_upsell_amount_infant = fields.Boolean('Apply Upsell Amount to Infant', default=False)

    tkt_sales_fare_percentage = fields.Float('Fare (%)', default=0)
    tkt_sales_fare_amount = fields.Float('Fare Amount', default=0)
    tkt_sales_tax_percentage = fields.Float('Tax (%)', default=0)
    tkt_sales_tax_amount = fields.Float('Tax Amount', default=0)
    tkt_sales_total_percentage = fields.Float('Total (%)', default=0)
    tkt_sales_total_amount = fields.Float('Total Amount', default=0)
    tkt_sales_upsell_percentage = fields.Float('Upsell (%)', default=0)
    tkt_sales_upsell_minimum = fields.Float('Upsell Minimum Amount', default=0)
    tkt_sales_upsell_amount = fields.Float('Upsell Amount', default=0)
    tkt_sales_upsell_route = fields.Boolean('Upsell per Route', default=False)
    tkt_sales_upsell_segment = fields.Boolean('Upsell per Segment', default=False)
    # tkt_sales_upsell_pax = fields.Boolean('Upsell per Pax', default=False)
    tkt_sales_fare_infant = fields.Boolean('Apply Fare Pricing to Infant', default=False)
    tkt_sales_tax_infant = fields.Boolean('Apply Tax Pricing to Infant', default=False)
    tkt_sales_total_infant = fields.Boolean('Apply Total Pricing to Infant', default=True)
    tkt_sales_upsell_percentage_infant = fields.Boolean('Apply Upsell Percentage to Infant', default=False)
    tkt_sales_upsell_amount_infant = fields.Boolean('Apply Upsell Amount to Infant', default=False)

    anc_nta_fare_percentage = fields.Float('Fare (%)', default=0)
    anc_nta_fare_amount = fields.Float('Fare Amount', default=0)
    anc_nta_tax_percentage = fields.Float('Tax (%)', default=0)
    anc_nta_tax_amount = fields.Float('Tax Amount', default=0)
    anc_nta_total_percentage = fields.Float('Total (%)', default=0)
    anc_nta_total_amount = fields.Float('Total Amount', default=0)
    anc_nta_upsell_percentage = fields.Float('Upsell (%)', default=0)
    anc_nta_upsell_minimum = fields.Float('Upsell Minimum Amount', default=0)
    anc_nta_upsell_amount = fields.Float('Upsell Amount', default=0)

    anc_sales_fare_percentage = fields.Float('Fare (%)', default=0)
    anc_sales_fare_amount = fields.Float('Fare Amount', default=0)
    anc_sales_tax_percentage = fields.Float('Tax (%)', default=0)
    anc_sales_tax_amount = fields.Float('Tax Amount', default=0)
    anc_sales_total_percentage = fields.Float('Total (%)', default=0)
    anc_sales_total_amount = fields.Float('Total Amount', default=0)
    anc_sales_upsell_percentage = fields.Float('Upsell (%)', default=0)
    anc_sales_upsell_minimum = fields.Float('Upsell Minimum Amount', default=0)
    anc_sales_upsell_amount = fields.Float('Upsell Amount', default=0)

    rsv_nta_upsell_amount = fields.Float('Upsell Amount', default=0)
    rsv_nta_upsell_route = fields.Boolean('Upsell per Route', default=False)
    rsv_nta_upsell_segment = fields.Boolean('Upsell per Segment', default=False)

    rsv_sales_upsell_amount = fields.Float('Upsell Amount', default=0)
    rsv_sales_upsell_route = fields.Boolean('Upsell per Route', default=False)
    rsv_sales_upsell_segment = fields.Boolean('Upsell per Segment', default=False)

    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)

    def get_data(self):
        res = {
            'id': self.id,
            'name': self.name if self.name else '',
            'set_expiration_date': self.set_expiration_date,
            'date_from': self.date_from.strftime(FORMAT_DATETIME) if self.set_expiration_date and self.date_from else '',
            'date_to': self.date_to.strftime(FORMAT_DATETIME) if self.set_expiration_date and self.date_to else '',
            'route': {
                'origin': {
                    'access_type': self.origin_access_type,
                    'destination_code_list': [rec.code for rec in self.origin_ids],
                    'city_code_list': [rec.code for rec in self.origin_city_ids],
                    'country_code_list': [rec.code for rec in self.origin_country_ids],
                },
                'destination': {
                    'access_type': self.destination_access_type,
                    'destination_code_list': [rec.code for rec in self.destination_ids],
                    'city_code_list': [rec.code for rec in self.destination_city_ids],
                    'country_code_list': [rec.code for rec in self.destination_country_ids],
                },
                'class_of_service': {
                    'access_type': self.class_of_service_access_type,
                    'class_of_service_list': [rec.strip() for rec in self.class_of_service_list.split(',')] if self.class_of_service_list else [],
                },
                'charge_code': {
                    'access_type': self.charge_code_access_type,
                    'charge_code_list': [rec.strip() for rec in self.charge_code_list.split(',')] if self.charge_code_list else [],
                }
            },
            'less': {
                'percentage': self.less_percentage,
                'is_infant': self.less_infant
            },
            'ticketing': {
                'nta': {
                    'fare': {
                        'percentage': self.tkt_nta_fare_percentage,
                        'amount': self.tkt_nta_fare_amount,
                        'is_infant': self.tkt_nta_fare_infant
                    },
                    'tax': {
                        'percentage': self.tkt_nta_tax_percentage,
                        'amount': self.tkt_nta_tax_amount,
                        'is_infant': self.tkt_nta_tax_infant
                    },
                    'total': {
                        'percentage': self.tkt_nta_total_percentage,
                        'amount': self.tkt_nta_total_amount,
                        'is_infant': self.tkt_nta_total_infant
                    },
                    'upsell_by_percentage': {
                        'percentage': self.tkt_nta_upsell_percentage,
                        'minimum': self.tkt_nta_upsell_minimum,
                        'is_infant': self.tkt_nta_upsell_percentage_infant
                    },
                    'upsell_by_amount': {
                        'amount': self.tkt_nta_upsell_amount,
                        'is_route': self.tkt_nta_upsell_route,
                        'is_segment': self.tkt_nta_upsell_segment,
                        # 'is_pax': self.tkt_nta_upsell_pax,
                        'is_infant': self.tkt_nta_upsell_amount_infant
                    }
                },
                'sales': {
                    'fare': {
                        'percentage': self.tkt_sales_fare_percentage,
                        'amount': self.tkt_sales_fare_amount,
                        'is_infant': self.tkt_sales_fare_infant
                    },
                    'tax': {
                        'percentage': self.tkt_sales_tax_percentage,
                        'amount': self.tkt_sales_tax_amount,
                        'is_infant': self.tkt_sales_tax_infant
                    },
                    'total': {
                        'percentage': self.tkt_sales_total_percentage,
                        'amount': self.tkt_sales_total_amount,
                        'is_infant': self.tkt_sales_total_infant
                    },
                    'upsell_by_percentage': {
                        'percentage': self.tkt_sales_upsell_percentage,
                        'minimum': self.tkt_sales_upsell_minimum,
                        'is_infant': self.tkt_sales_upsell_percentage_infant
                    },
                    'upsell_by_amount': {
                        'amount': self.tkt_sales_upsell_amount,
                        'is_route': self.tkt_sales_upsell_route,
                        'is_segment': self.tkt_sales_upsell_segment,
                        # 'is_pax': self.tkt_sales_upsell_pax,
                        'is_infant': self.tkt_sales_upsell_amount_infant
                    }
                }
            },
            'ancillary': {
                'nta': {
                    'fare': {
                        'percentage': self.anc_nta_fare_percentage,
                        'amount': self.anc_nta_fare_amount,
                    },
                    'tax': {
                        'percentage': self.anc_nta_tax_percentage,
                        'amount': self.anc_nta_tax_amount,
                    },
                    'total': {
                        'percentage': self.anc_nta_total_percentage,
                        'amount': self.anc_nta_total_amount,
                    },
                    'upsell_by_percentage': {
                        'percentage': self.anc_nta_upsell_percentage,
                        'minimum': self.anc_nta_upsell_minimum,
                    },
                    'upsell_by_amount': {
                        'amount': self.anc_nta_upsell_amount,
                    }
                },
                'sales': {
                    'fare': {
                        'percentage': self.anc_sales_fare_percentage,
                        'amount': self.anc_sales_fare_amount,
                    },
                    'tax': {
                        'percentage': self.anc_sales_tax_percentage,
                        'amount': self.anc_sales_tax_amount,
                    },
                    'total': {
                        'percentage': self.anc_sales_total_percentage,
                        'amount': self.anc_sales_total_amount,
                    },
                    'upsell_by_percentage': {
                        'percentage': self.anc_sales_upsell_percentage,
                        'minimum': self.anc_sales_upsell_minimum,
                    },
                    'upsell_by_amount': {
                        'amount': self.anc_sales_upsell_amount,
                    }
                }
            },
            'reservation': {
                'nta': {
                    'upsell_by_amount': {
                        'amount': self.rsv_nta_upsell_amount,
                        'is_route': self.rsv_nta_upsell_route,
                        'is_segment': self.rsv_nta_upsell_segment,
                    }
                },
                'sales': {
                    'upsell_by_amount': {
                        'amount': self.rsv_sales_upsell_amount,
                        'is_route': self.rsv_sales_upsell_route,
                        'is_segment': self.rsv_sales_upsell_segment,
                    }
                }
            },
            'state': self.state,
        }
        return res
