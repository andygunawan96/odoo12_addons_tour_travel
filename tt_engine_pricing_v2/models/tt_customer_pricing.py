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

ACCESS_TYPE_2 = [
    ('all', 'ALL'),
    ('allow', 'Allowed'),
    ('restrict', 'Restricted'),
    ('if_any', 'If any value'),
    ('if_blank', 'If no value'),
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

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=False, default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, default=lambda self: self.env.user.agent_id)

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
                    if str(obj.ho_id.id) not in customer_pricing_data:
                        customer_pricing_data[str(obj.ho_id.id)] = {}
                        vals = obj.get_data()
                        agent_id = str(vals['agent_id'])
                        if agent_id not in customer_pricing_data[str(obj.ho_id.id)]:
                            customer_pricing_data[str(obj.ho_id.id)][agent_id] = {
                                'customer_pricing_list': [],
                                'create_date': date_now,
                                'expired_date': expired_date,
                            }
                        customer_pricing_data[str(obj.ho_id.id)][agent_id]['customer_pricing_list'].append(vals)

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
    set_expiration_date = fields.Boolean('Set Expiration Date', default=False)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')

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

    def get_data(self):
        res = {
            'id': self.id,
            'sequence': self.sequence,
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
                },
                'tour_code': {
                    'access_type': self.tour_code_access_type,
                    'tour_code_list': [rec.strip() for rec in self.tour_code_list.split(',')] if self.tour_code_list else [],
                },
                'date_of_travel': {
                    'access_type': self.dot_access_type,
                    'start_date': self.dot_start_date.strftime('%Y-%m-%d %H:%M:%S') if self.dot_start_date else '',
                    'end_date': self.dot_end_date.strftime('%Y-%m-%d %H:%M:%S') if self.dot_end_date else '',
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
                }
            },
            'state': self.state,
        }
        return res
