from odoo import models, fields, api, _
from ...tools.db_connector import GatewayConnector
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

ACCESS_TYPE_2 = [
    ('all', 'ALL'),
    ('allow', 'Allowed'),
    ('restrict', 'Restricted'),
    ('if_any', 'If any value'),
    ('if_blank', 'If no value'),
]

ACCESS_TYPE_3 = [
    ('all', 'ALL'),
    ('less', 'Less'),
    ('greater', 'Greater'),
    ('between', 'In between'),
]

STATE = [
    ('enable', 'Enable'),
    ('disable', 'Disable'),
]

FORMAT_DATETIME = '%Y-%m-%d %H:%M:%S'
EXPIRED_SECONDS = 300


class CustomerPricing(models.Model):
    _name = 'tt.customer.pricing'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Customer Pricing'

    name = fields.Char('Name', compute='_compute_name', store=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, default=lambda self: self.env.user.agent_id)
    pricing_breakdown = fields.Boolean('Pricing Breakdown', related='ho_id.pricing_breakdown', store=True)

    customer_parent_type_name = fields.Char('Customer Parent Type Name', compute='_compute_customer_parent_type_name', store=True)
    customer_parent_type_access_type = fields.Selection(ACCESS_TYPE, 'Customer Parent Type Access Type', default='allow', required=True)
    customer_parent_type_ids = fields.Many2many('tt.customer.parent.type', 'tt_customer_pricing_customer_parent_type_rel', 'pricing_id', 'customer_parent_type_id', string='Customer Parent Types')

    customer_parent_name = fields.Char('Customer Parent Name', compute='_compute_customer_parent_name', store=True)
    customer_parent_access_type = fields.Selection(ACCESS_TYPE, 'Customer Parent Access Type', default='all', required=True)
    customer_parent_ids = fields.Many2many('tt.customer.parent', 'tt_customer_pricing_customer_parent_rel', 'pricing_id', 'customer_parent_id', string='Customer Parentd', domain="[('parent_agent_id', '=', agent_id)]")

    provider_type_name = fields.Char('Provider Type Name', compute='_compute_provider_type_name', store=True)
    provider_type_access_type = fields.Selection(ACCESS_TYPE, 'Provider Type Access Type', default='all', required=True)
    provider_type_ids = fields.Many2many('tt.provider.type', 'tt_customer_pricing_provider_type_rel', 'pricing_id', 'provider_type_id',
                                         string='Provider Types')

    provider_name = fields.Char('Provider Name', compute='_compute_provider_name', store=True)
    provider_access_type = fields.Selection(ACCESS_TYPE, 'Provider Access Type', default='all', required=True)
    provider_ids = fields.Many2many('tt.provider', 'tt_customer_pricing_provider_rel', 'pricing_id', 'provider_id',
                                    string='Providers')

    carrier_name = fields.Char('Carrier Name', compute='_compute_carrier_name', store=True)
    carrier_access_type = fields.Selection(ACCESS_TYPE, 'Carrier Access Type', default='all', required=True)
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_customer_pricing_carrier_rel', 'pricing_id', 'carrier_id',
                                   string='Carriers')

    line_ids = fields.One2many('tt.customer.pricing.line', 'pricing_id', string='Rules', context={'active_test': False}, copy=True)

    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals):
        res = super(CustomerPricing, self).create(vals)
        try:
            data = {
                'code': 9901,
                'title': 'CUSTOMER PRICING',
                'message': 'New customer pricing created: %s\nUser: %s\n' % (
                    res.name, self.env.user.name)
            }
            context = {
                "co_ho_id": res.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "customer pricing changes" telegram notification: ' + str(e))
        return res

    def write(self, vals):
        super(CustomerPricing, self).write(vals)
        try:
            data = {
                'code': 9901,
                'title': 'CUSTOMER PRICING',
                'message': 'Customer pricing modified: %s\nUser: %s\n' % (
                    self.name, self.env.user.name)
            }
            context = {
                "co_ho_id": self.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "customer pricing changes" telegram notification: ' + str(e))

    @api.depends('agent_id', 'provider_type_name', 'provider_name', 'carrier_name', 'customer_parent_type_name', 'customer_parent_name')
    def _compute_name(self):
        for rec in self:
            name_list = []
            if rec.agent_id:
                name_list.append(rec.agent_id.name)
            if rec.customer_parent_type_name:
                name_list.append('[%s]' % rec.customer_parent_type_name)
            if rec.customer_parent_name:
                name_list.append('[%s]' % rec.customer_parent_name)
            if rec.provider_type_name:
                name_list.append('[%s]' % rec.provider_type_name)
            if rec.provider_name:
                name_list.append('[%s]' % rec.provider_name)
            if rec.carrier_name:
                name_list.append('[%s]' % rec.carrier_name)

            name = ' '.join(name_list)
            rec.name = name

    @api.depends('customer_parent_type_access_type', 'customer_parent_type_ids')
    def _compute_customer_parent_type_name(self):
        for rec in self:
            name_list = []
            customer_parent_type_name = 'In All Customer Parent Types'
            if rec.customer_parent_type_access_type != 'all':
                for cust_type in rec.customer_parent_type_ids:
                    name_list.append('%s' % cust_type.name)
                customer_parent_type_name = '%s in Customer Parent Type %s' % (rec.customer_parent_type_access_type.title(), ','.join(name_list))
            rec.customer_parent_type_name = customer_parent_type_name

    @api.depends('customer_parent_access_type', 'customer_parent_ids')
    def _compute_customer_parent_name(self):
        for rec in self:
            name_list = []
            customer_parent_name = 'In All Customer Parents'
            if rec.customer_parent_access_type != 'all':
                for cust_type in rec.customer_parent_ids:
                    name_list.append('%s' % cust_type.name)
                customer_parent_name = '%s in Customer Parent %s' % (rec.customer_parent_access_type.title(), ','.join(name_list))
            rec.customer_parent_name = customer_parent_name

    @api.depends('provider_type_access_type', 'provider_type_ids')
    def _compute_provider_type_name(self):
        for rec in self:
            name_list = []
            provider_type_name = 'In All Provider Types'
            if rec.provider_type_access_type != 'all':
                for prov_type in rec.provider_type_ids:
                    name_list.append('%s' % prov_type.name)
                provider_type_name = '%s in Provider Type %s' % (rec.provider_type_access_type.title(), ','.join(name_list))
            rec.provider_type_name = provider_type_name

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
        _logger.info(msg)
        return True

    def get_data(self):
        res = {
            'id': self.id,
            'sequence': self.sequence,
            'name': self.name if self.name else '',
            'agent_id': self.agent_id.id if self.agent_id else '',
            'customer_parent_type': {
                'access_type': self.customer_parent_type_access_type,
                'customer_parent_type_code_list': [rec.code for rec in self.customer_parent_type_ids]
            },
            'customer_parent': {
                'access_type': self.customer_parent_access_type,
                'customer_parent_id_list': [rec.id for rec in self.customer_parent_ids]
            },
            'provider': {
                'access_type': self.provider_access_type,
                'provider_code_list': [rec.code for rec in self.provider_ids]
            },
            'carrier': {
                'access_type': self.carrier_access_type,
                'carrier_code_list': [rec.code for rec in self.carrier_ids]
            },
            'provider_type': {
                'access_type': self.provider_type_access_type,
                'provider_type_code_list': [rec.code for rec in self.provider_type_ids]
            },
            'rule_list': [rec.get_data() for rec in self.line_ids if rec.active],
            'state': self.state,
        }
        return res

    def get_customer_pricing_api(self):
        try:
            objs = self.env['tt.customer.pricing'].sudo().search([])
            customer_pricing_data = {}
            date_now = datetime.now().strftime(FORMAT_DATETIME)
            expired_date = datetime.now() + timedelta(seconds=EXPIRED_SECONDS)
            expired_date = expired_date.strftime(FORMAT_DATETIME)
            for obj in objs:
                if not obj.active:
                    continue
                if obj.ho_id:
                    ho_id = str(obj.ho_id.id)
                    if ho_id not in customer_pricing_data:
                        customer_pricing_data[ho_id] = {}
                    vals = obj.get_data()
                    agent_id = str(vals['agent_id'])
                    if agent_id not in customer_pricing_data[ho_id]:
                        customer_pricing_data[ho_id][agent_id] = {
                            'customer_pricing_list': [],
                            'create_date': date_now,
                            'expired_date': expired_date,
                        }
                    customer_pricing_data[ho_id][agent_id]['customer_pricing_list'].append(vals)

            payload = {
                'customer_pricing_data': customer_pricing_data
            }
        except Exception as e:
            _logger.error('Error Get Customer Pricing Data, %s' % traceback.format_exc())
            payload = {}
        return payload


class CustomerPricingLine(models.Model):
    _name = 'tt.customer.pricing.line'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Customer Pricing Line'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    pricing_id = fields.Many2one('tt.customer.pricing', 'Customer Pricing', readonly=1, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', 'Currency', ondelete='cascade')
    set_expiration_date = fields.Boolean('Set Expiration Date', default=False)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')
    pricing_breakdown = fields.Boolean('Pricing Breakdown', related='pricing_id.pricing_breakdown', store=True)

    origin_name = fields.Char('Origin Name')
    origin_access_type = fields.Selection(ACCESS_TYPE, 'Origin Access Type', default='all', required=True)
    origin_ids = fields.Many2many('tt.destinations', 'tt_customer_pricing_destinations_origin_rel',
                                  'pricing_line_id', 'destination_id', string='Origin')
    origin_city_ids = fields.Many2many('res.city', 'tt_customer_pricing_city_origin_rel',
                                       'pricing_line_id', 'city_id', string='Origin Cities')
    origin_country_ids = fields.Many2many('res.country', 'tt_customer_pricing_country_origin_rel',
                                          'pricing_line_id', 'country_id', string='Origin Countries')

    destination_name = fields.Char('Destination Name')
    destination_access_type = fields.Selection(ACCESS_TYPE, 'Destination Access Type', default='all', required=True)
    destination_ids = fields.Many2many('tt.destinations', 'tt_customer_pricing_destinations_destination_rel',
                                       'pricing_line_id', 'destination_id', string='Destination')
    destination_city_ids = fields.Many2many('res.city', 'tt_customer_pricing_city_destination_rel',
                                            'pricing_line_id', 'city_id', string='Destination Cities')
    destination_country_ids = fields.Many2many('res.country', 'tt_customer_pricing_country_destination_rel',
                                               'pricing_line_id', 'country_id', string='Destination Countries')

    class_of_service_name = fields.Char('Class of Service Name')
    class_of_service_access_type = fields.Selection(ACCESS_TYPE, 'Class of Service Access Type', default='all', required=True)
    class_of_service_list = fields.Char('Class of Service List', help='Use comma (,) for separate the values')

    charge_code_name = fields.Char('Charge Code Name')
    charge_code_access_type = fields.Selection(ACCESS_TYPE, 'Charge Code Access Type', default='all', required=True)
    charge_code_list = fields.Char('Charge Code List', help='Use comma (,) for separate the values')

    tour_code_name = fields.Char('Tour Code Name')
    tour_code_access_type = fields.Selection(ACCESS_TYPE_2, 'Tour Code Access Type', default='all', required=True)
    tour_code_list = fields.Char('Tour Code List', help='Use comma (,) for separate the values')

    dot_name = fields.Char('DOT Name')
    dot_access_type = fields.Selection(ACCESS_TYPE, 'DOT Access Type', default='all', required=True)
    dot_start_date = fields.Datetime('Start DOT')
    dot_end_date = fields.Datetime('End DOT')

    tkt_sales_upsell_percentage = fields.Float('Upsell (%)', default=0)
    tkt_sales_upsell_minimum = fields.Float('Minimum Amount', default=0)
    tkt_sales_upsell_has_minimum = fields.Boolean('Has Minimum', default=True)
    tkt_sales_upsell_maximum = fields.Float('Maximum Amount', default=0)
    tkt_sales_upsell_has_maximum = fields.Boolean('Has Maximum', default=False)
    tkt_sales_upsell_percentage_infant = fields.Boolean('Apply Upsell Percentage to Infant', default=False)
    tkt_sales_upsell_amount = fields.Float('Upsell Amount', default=0)
    tkt_sales_upsell_route = fields.Boolean('Upsell per Route', default=False)
    tkt_sales_upsell_segment = fields.Boolean('Upsell per Segment', default=False)
    # tkt_sales_upsell_pax = fields.Boolean('Upsell per Pax', default=False)
    tkt_sales_upsell_amount_infant = fields.Boolean('Apply Upsell Amount to Infant', default=False)

    anc_sales_upsell_percentage = fields.Float('Upsell (%)', default=0)
    anc_sales_upsell_minimum = fields.Float('Minimum Amount', default=0)
    anc_sales_upsell_has_minimum = fields.Boolean('Has Minimum', default=True)
    anc_sales_upsell_maximum = fields.Float('Maximum Amount', default=0)
    anc_sales_upsell_has_maximum = fields.Boolean('Has Maximum', default=False)
    anc_sales_upsell_amount = fields.Float('Upsell Amount', default=0)

    rsv_sales_upsell_amount = fields.Float('Upsell Amount', default=0)
    rsv_sales_upsell_route = fields.Boolean('Upsell per Route', default=False)
    rsv_sales_upsell_segment = fields.Boolean('Upsell per Segment', default=False)
    rsv_sales_upsell_percentage = fields.Float('Upsell (%)', default=0)
    rsv_sales_upsell_minimum = fields.Float('Minimum Amount', default=0)
    rsv_sales_upsell_has_minimum = fields.Boolean('Has Minimum', default=False)
    rsv_sales_upsell_maximum = fields.Float('Maximum Amount', default=0)
    rsv_sales_upsell_has_maximum = fields.Boolean('Has Maximum', default=False)

    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)

    # August 15, 2023 - SAM
    rsv_com_tax_amount = fields.Float('Commission Tax Amount', default=0)
    rsv_com_tax_percentage = fields.Float('Commission Tax Percentage (%)', default=0)
    rsv_com_rounding_places = fields.Integer('Commission Rounding Places', default=0)
    tkt_com_tax_amount = fields.Float('Commission Tax Amount', default=0)
    tkt_com_tax_percentage = fields.Float('Commission Tax Percentage (%)', default=0)
    tkt_com_rounding_places = fields.Integer('Commission Rounding Places', default=0)
    anc_com_tax_amount = fields.Float('Commission Tax Amount', default=0)
    anc_com_tax_percentage = fields.Float('Commission Tax Percentage (%)', default=0)
    anc_com_rounding_places = fields.Integer('Commission Rounding Places', default=0)

    total_name = fields.Char('Amount Name')
    total_access_type = fields.Selection(ACCESS_TYPE_3, 'Amount Access Type', default='all', required=True)
    total_is_less_equal = fields.Boolean('Is Less Equal to', default=False)
    total_less_amount = fields.Float('Less than amount', default=0.0)
    total_is_greater_equal = fields.Boolean('Is Greater Equal to', default=False)
    total_greater_amount = fields.Float('Greater than amount', default=0.0)
    # END

    # October 17, 2023 - SAM
    rsv_ho_com_tax_amount = fields.Float('Commission Tax Amount', default=0)
    rsv_ho_com_tax_percentage = fields.Float('Commission Tax Percentage (%)', default=0)
    rsv_ho_com_rounding_places = fields.Integer('Commission Rounding Places', default=0)
    tkt_ho_com_tax_amount = fields.Float('Commission Tax Amount', default=0)
    tkt_ho_com_tax_percentage = fields.Float('Commission Tax Percentage (%)', default=0)
    tkt_ho_com_rounding_places = fields.Integer('Commission Rounding Places', default=0)
    anc_ho_com_tax_amount = fields.Float('Commission Tax Amount', default=0)
    anc_ho_com_tax_percentage = fields.Float('Commission Tax Percentage (%)', default=0)
    anc_ho_com_rounding_places = fields.Integer('Commission Rounding Places', default=0)

    # END

    @api.model
    def create(self, vals):
        res = super(CustomerPricingLine, self).create(vals)
        try:
            data = {
                'code': 9901,
                'title': 'CUSTOMER PRICING LINE',
                'message': 'New customer pricing line created: %s (%s)\nUser: %s\n' % (
                    res.name, res.pricing_id.name, self.env.user.name)
            }
            context = {
                "co_ho_id": res.pricing_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "customer pricing line changes" telegram notification: ' + str(e))
        return res

    def write(self, vals):
        super(CustomerPricingLine, self).write(vals)
        try:
            data = {
                'code': 9901,
                'title': 'CUSTOMER PRICING LINE',
                'message': 'Customer pricing line modified: %s (%s)\nUser: %s\n' % (
                    self.name, self.pricing_id.name, self.env.user.name)
            }
            context = {
                "co_ho_id": self.pricing_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "customer pricing line changes" telegram notification: ' + str(e))

    @api.onchange('tkt_ho_com_tax_percentage')
    def _onchange_tkt_ho_com_tax_percentage(self):
        if self.tkt_ho_com_tax_percentage < 0:
            return {
                'warning': {
                    'title': "Value will be ignored",
                    'message': "Please use value >= 0",
                }
            }
        else:
            return {}

    @api.onchange('tkt_ho_com_tax_amount')
    def _onchange_tkt_ho_com_tax_amount(self):
        if self.tkt_ho_com_tax_amount < 0:
            return {
                'warning': {
                    'title': "Value will be ignored",
                    'message': "Please use value >= 0",
                }
            }
        else:
            return {}

    @api.onchange('rsv_ho_com_tax_percentage')
    def _onchange_rsv_ho_com_tax_percentage(self):
        if self.rsv_ho_com_tax_percentage < 0:
            return {
                'warning': {
                    'title': "Value will be ignored",
                    'message': "Please use value >= 0",
                }
            }
        else:
            return {}

    @api.onchange('rsv_ho_com_tax_amount')
    def _onchange_rsv_ho_com_tax_amount(self):
        if self.rsv_ho_com_tax_amount < 0:
            return {
                'warning': {
                    'title': "Value will be ignored",
                    'message': "Please use value >= 0",
                }
            }
        else:
            return {}

    @api.onchange('tkt_com_tax_percentage')
    def _onchange_tkt_com_tax_percentage(self):
        if self.tkt_com_tax_percentage > 0:
            return {
                'warning': {
                    'title': "Value will be ignored",
                    'message': "Please use value <= 0",
                }
            }
        else:
            return {}

    @api.onchange('tkt_com_tax_amount')
    def _onchange_tkt_com_tax_amount(self):
        if self.tkt_com_tax_amount > 0:
            return {
                'warning': {
                    'title': "Value will be ignored",
                    'message': "Please use value <= 0",
                }
            }
        else:
            return {}

    @api.onchange('rsv_com_tax_percentage')
    def _onchange_rsv_com_tax_percentage(self):
        if self.rsv_com_tax_percentage > 0:
            return {
                'warning': {
                    'title': "Value will be ignored",
                    'message': "Please use value <= 0",
                }
            }
        else:
            return {}

    @api.onchange('rsv_com_tax_amount')
    def _onchange_rsv_com_tax_amount(self):
        if self.rsv_com_tax_amount > 0:
            return {
                'warning': {
                    'title': "Value will be ignored",
                    'message': "Please use value <= 0",
                }
            }
        else:
            return {}

    def get_data(self):
        res = {
            'id': self.id,
            'sequence': self.sequence,
            'name': self.name if self.name else '',
            'set_expiration_date': self.set_expiration_date,
            'currency_code': self.currency_id.name if self.currency_id else '',
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
                },
                'tour_code': {
                    'access_type': self.tour_code_access_type,
                    'tour_code_list': [rec.strip() for rec in self.tour_code_list.split(',')] if self.tour_code_list else [],
                },
                'date_of_travel': {
                    'access_type': self.dot_access_type,
                    'start_date': self.dot_start_date.strftime('%Y-%m-%d %H:%M:%S') if self.dot_start_date else '',
                    'end_date': self.dot_end_date.strftime('%Y-%m-%d %H:%M:%S') if self.dot_end_date else '',
                },
                'total': {
                    'access_type': self.total_access_type,
                    'is_less_equal': self.total_is_less_equal,
                    'less_amount': self.total_less_amount,
                    'is_greater_equal': self.total_is_greater_equal,
                    'greater_amount': self.total_greater_amount,
                }
            },
            'ticketing': {
                'sales': {
                    'upsell_by_percentage': {
                        'percentage': self.tkt_sales_upsell_percentage,
                        'minimum': self.tkt_sales_upsell_minimum,
                        'has_minimum': self.tkt_sales_upsell_has_minimum,
                        'maximum': self.tkt_sales_upsell_maximum,
                        'has_maximum': self.tkt_sales_upsell_has_maximum,
                        'is_infant': self.tkt_sales_upsell_percentage_infant
                    },
                    'upsell_by_amount': {
                        'amount': self.tkt_sales_upsell_amount,
                        'is_route': self.tkt_sales_upsell_route,
                        'is_segment': self.tkt_sales_upsell_segment,
                        # 'is_pax': self.tkt_sales_upsell_pax,
                        'is_infant': self.tkt_sales_upsell_amount_infant
                    }
                },
                'commission': {
                    'tax_amount': self.tkt_com_tax_amount,
                    'tax_percentage': self.tkt_com_tax_percentage,
                    'rounding': self.tkt_com_rounding_places,
                },
                'ho_commission': {
                    'tax_amount': self.tkt_ho_com_tax_amount,
                    'tax_percentage': self.tkt_ho_com_tax_percentage,
                    'rounding': self.tkt_ho_com_rounding_places,
                }
            },
            'ancillary': {
                'sales': {
                    'upsell_by_percentage': {
                        'percentage': self.anc_sales_upsell_percentage,
                        'minimum': self.anc_sales_upsell_minimum,
                        'has_minimum': self.anc_sales_upsell_has_minimum,
                        'maximum': self.anc_sales_upsell_maximum,
                        'has_maximum': self.anc_sales_upsell_has_maximum,
                    },
                    'upsell_by_amount': {
                        'amount': self.anc_sales_upsell_amount,
                    }
                },
                'commission': {
                    'tax_amount': self.anc_com_tax_amount,
                    'tax_percentage': self.anc_com_tax_percentage,
                    'rounding': self.anc_com_rounding_places,
                },
                'ho_commission': {
                    'tax_amount': self.anc_ho_com_tax_amount,
                    'tax_percentage': self.anc_ho_com_tax_percentage,
                    'rounding': self.anc_ho_com_rounding_places,
                }
            },
            'reservation': {
                'sales': {
                    'upsell_by_amount': {
                        'amount': self.rsv_sales_upsell_amount,
                        'is_route': self.rsv_sales_upsell_route,
                        'is_segment': self.rsv_sales_upsell_segment,
                    },
                    'upsell_by_percentage': {
                        'percentage': self.rsv_sales_upsell_percentage,
                        'minimum': self.rsv_sales_upsell_minimum,
                        'has_minimum': self.rsv_sales_upsell_has_minimum,
                        'maximum': self.rsv_sales_upsell_maximum,
                        'has_maximum': self.rsv_sales_upsell_has_maximum,
                    },
                },
                'commission': {
                    'tax_amount': self.rsv_com_tax_amount,
                    'tax_percentage': self.rsv_com_tax_percentage,
                    'rounding': self.rsv_com_rounding_places,
                },
                'ho_commission': {
                    'tax_amount': self.rsv_ho_com_tax_amount,
                    'tax_percentage': self.rsv_ho_com_tax_percentage,
                    'rounding': self.rsv_ho_com_rounding_places,
                }
            },
            'pricing_breakdown': self.pricing_breakdown,
            'state': self.state,
        }
        return res
