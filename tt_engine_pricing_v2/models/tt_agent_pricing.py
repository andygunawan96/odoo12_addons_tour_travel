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


class AgentPricing(models.Model):
    _name = 'tt.agent.pricing'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Agent Pricing'

    name = fields.Char('Name', compute='_compute_name', store=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)

    provider_type_name = fields.Char('Provider Type Name', compute='_compute_provider_type_name', store=True)
    provider_type_access_type = fields.Selection(ACCESS_TYPE, 'Provider Type Access Type', default='allow', required=True)
    provider_type_ids = fields.Many2many('tt.provider.type', 'tt_agent_pricing_provider_type_rel', 'pricing_id', 'provider_type_id',
                                         string='Provider Types')

    agent_name = fields.Char('Agent Name', compute='_compute_agent_name', store=True)
    agent_access_type = fields.Selection(ACCESS_TYPE, 'Agent Access Type', default='all', required=True)
    agent_ids = fields.Many2many('tt.agent', 'tt_agent_pricing_agent_rel', 'pricing_id',
                                 'agent_id', string='Agents', domain='[("agent_type_id", "=", agent_type_id)]')

    provider_name = fields.Char('Provider Name', compute='_compute_provider_name', store=True)
    provider_access_type = fields.Selection(ACCESS_TYPE, 'Provider Access Type', default='all', required=True)
    provider_ids = fields.Many2many('tt.provider', 'tt_agent_pricing_provider_rel', 'pricing_id', 'provider_id',
                                    string='Providers')

    carrier_name = fields.Char('Carrier Name', compute='_compute_carrier_name', store=True)
    carrier_access_type = fields.Selection(ACCESS_TYPE, 'Carrier Access Type', default='all', required=True)
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_agent_pricing_carrier_rel', 'pricing_id', 'carrier_id',
                                   string='Carriers')

    line_ids = fields.One2many('tt.agent.pricing.line', 'pricing_id', string='Rules', context={'active_test': False})

    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)

    @api.depends('agent_type_id', 'provider_type_name', 'agent_name', 'provider_name', 'carrier_name')
    def _compute_name(self):
        for rec in self:
            name_list = []
            if rec.agent_type_id:
                name_list.append(rec.agent_type_id.name)
            if rec.agent_name:
                name_list.append('[%s]' % rec.agent_name)
            if rec.carrier_name:
                name_list.append('[%s]' % rec.carrier_name)
            if rec.provider_type_name:
                name_list.append('[%s]' % rec.provider_type_name)
            if rec.provider_name:
                name_list.append('[%s]' % rec.provider_name)

            name = ' '.join(name_list)
            rec.name = name

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

    @api.depends('agent_access_type', 'agent_ids')
    def _compute_agent_name(self):
        for rec in self:
            name_list = []
            agent_name = 'for All Agents'
            if rec.agent_access_type != 'all':
                for agent in rec.agent_ids:
                    name_list.append('%s' % agent.name)
                agent_name = '%s for %s' % (rec.agent_access_type.title(), ','.join(name_list))
            rec.agent_name = agent_name

    def test_get_data(self):
        res = self.get_data()
        msg = 'Get Data : %s' % json.dumps(res)
        print(msg)
        _logger.info(msg)
        return True

    def get_data(self):
        res = {
            'name': self.name if self.name else '',
            'agent_type_code': self.agent_type_id.code if self.agent_type_id else '',
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
            'agent': {
                'access_type': self.agent_access_type,
                'agent_id_list': [rec.id for rec in self.agent_ids]
            },
            'rule_list': [rec.get_data() for rec in self.line_ids],
            'state': self.state,
        }
        return res

    def get_agent_pricing_api(self):
        try:
            objs = self.env['tt.agent.pricing'].sudo().search([])
            agent_pricing_data = {}
            date_now = datetime.now().strftime(FORMAT_DATETIME)
            expired_date = datetime.now() + timedelta(seconds=EXPIRED_SECONDS)
            expired_date = expired_date.strftime(FORMAT_DATETIME)
            for obj in objs:
                if not obj.active or obj.state == 'disable':
                    continue

                vals = obj.get_data()
                agent_type_code = vals['agent_type_code']
                if agent_type_code not in agent_pricing_data:
                    agent_pricing_data[agent_type_code] = {
                        'agent_pricing_list': [],
                        'create_date': date_now,
                        'expired_date': expired_date,
                    }
                agent_pricing_data[agent_type_code]['agent_pricing_list'].append(vals)

            payload = {
                'agent_pricing_data': agent_pricing_data
            }
        except Exception as e:
            _logger.error('Error Get Agent Pricing Data, %s' % traceback.format_exc())
            payload = {}
        return payload


class AgentPricingLine(models.Model):
    _name = 'tt.agent.pricing.line'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Agent Pricing Line'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    pricing_id = fields.Many2one('tt.agent.pricing', 'Agent Pricing', readonly=1, ondelete='cascade')
    set_expiration_date = fields.Boolean('Set Expiration Date', default=False)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')

    origin_name = fields.Char('Origin Name')
    origin_access_type = fields.Selection(ACCESS_TYPE, 'Origin Access Type', default='all', required=True)
    origin_ids = fields.Many2many('tt.destinations', 'tt_agent_pricing_destinations_rel',
                                  'pricing_line_id', 'destination_id', string='Origin')
    origin_city_ids = fields.Many2many('res.city', 'tt_agent_pricing_city_rel',
                                       'pricing_line_id', 'city_id', string='Origin Cities')
    origin_country_ids = fields.Many2many('res.country', 'tt_agent_pricing_country_rel',
                                          'pricing_line_id', 'country_id', string='Origin Countries')

    destination_name = fields.Char('Destination Name')
    destination_access_type = fields.Selection(ACCESS_TYPE, 'Destination Access Type', default='all', required=True)
    destination_ids = fields.Many2many('tt.destinations', 'tt_agent_pricing_destinations_rel',
                                       'pricing_line_id', 'destination_id', string='Destination')
    destination_city_ids = fields.Many2many('res.city', 'tt_agent_pricing_city_rel',
                                            'pricing_line_id', 'city_id', string='Destination Cities')
    destination_country_ids = fields.Many2many('res.country', 'tt_agent_pricing_country_rel',
                                               'pricing_line_id', 'country_id', string='Destination Countries')

    class_of_service_name = fields.Char('Class of Service Name')
    class_of_service_access_type = fields.Selection(ACCESS_TYPE, 'Class of Service Access Type', default='all', required=True)
    class_of_service_list = fields.Char('Class of Service List', help='Use comma (,) for separate the values')

    charge_code_name = fields.Char('Charge Code Name')
    charge_code_access_type = fields.Selection(ACCESS_TYPE, 'Charge Code Access Type', default='all', required=True)
    charge_code_list = fields.Char('Charge Code List', help='Use comma (,) for separate the values')

    parent_charge_percentage = fields.Float('Parent Charge (%)', default=0)
    parent_charge_minimum = fields.Float('Parent Charge Minimum', default=0)
    parent_charge_amount = fields.Float('Parent Charge Amount', default=0)
    parent_charge_route = fields.Boolean('Parent Charge Route', default=False)
    parent_charge_segment = fields.Boolean('Parent Charge Segment', default=False)
    parent_charge_pax = fields.Boolean('Parent Charge Pax', default=False)
    parent_charge_infant = fields.Boolean('Parent Charge Include Infant', default=False)
    ho_charge_percentage = fields.Float('HO Charge (%)', default=0)
    ho_charge_minimum = fields.Float('HO Charge Minimum', default=0)
    ho_charge_amount = fields.Float('HO Charge Amount', default=0)
    ho_charge_route = fields.Boolean('HO Charge Route', default=False)
    ho_charge_segment = fields.Boolean('HO Charge Segment', default=False)
    ho_charge_pax = fields.Boolean('HO Charge Pax', default=False)
    ho_charge_infant = fields.Boolean('HO Charge Include Infant', default=False)
    commission_percentage = fields.Float('Commission (%)', default=0)
    commission_minimum = fields.Float('Commission Minimum', default=0)
    commission_amount = fields.Float('Commission Amount', default=0)
    commission_route = fields.Boolean('Commission Route', default=False)
    commission_segment = fields.Boolean('Commission Segment', default=False)
    commission_pax = fields.Boolean('Commission Pax', default=False)
    commission_infant = fields.Boolean('Commission Include Infant', default=False)
    upline_name = fields.Char('Upline Name', compute='_compute_upline_name')
    upline_ids = fields.One2many('tt.agent.pricing.upline', 'pricing_line_id', string='Uplines', context={'active_test': False})
    residual_amount_to = fields.Selection([
        ('ho', 'Head Office'),
        ('parent', 'Parent Agent'),
        ('agent', 'Agent'),
    ], 'Residual Amount To', default='ho')

    tkt_sales_upsell_percentage = fields.Float('Upsell (%)', default=0)
    tkt_sales_upsell_minimum = fields.Float('Upsell Minimum Amount', default=0)
    tkt_sales_upsell_percentage_infant = fields.Boolean('Apply Upsell Percentage to Infant', default=False)
    tkt_sales_upsell_amount = fields.Float('Upsell Amount', default=0)
    tkt_sales_upsell_route = fields.Boolean('Upsell per Route', default=False)
    tkt_sales_upsell_segment = fields.Boolean('Upsell per Segment', default=False)
    # tkt_sales_upsell_pax = fields.Boolean('Upsell per Pax', default=False)
    tkt_sales_upsell_amount_infant = fields.Boolean('Apply Upsell Amount to Infant', default=False)

    anc_sales_upsell_percentage = fields.Float('Upsell (%)', default=0)
    anc_sales_upsell_minimum = fields.Float('Upsell Minimum Amount', default=0)
    anc_sales_upsell_amount = fields.Float('Upsell Amount', default=0)

    rsv_sales_upsell_amount = fields.Float('Upsell Amount', default=0)
    rsv_sales_upsell_route = fields.Boolean('Upsell per Route', default=False)
    rsv_sales_upsell_segment = fields.Boolean('Upsell per Segment', default=False)

    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)

    # @api.depends('upline_ids')
    # def _compute_upline_name(self):
    #     for rec in self:
    #         upline_dict = {}
    #         for upline in rec.upline_ids:
    #             agent_type_code = upline.agent_type_id.code
    #             if agent_type_code not in upline_dict:
    #                 upline_dict[agent_type_code] = 0
    #             upline_dict[agent_type_code] += 1
    #
    #             name = upline.agent_type_id.name
    #             # if upline_dict[agent_type_code] > 1:
    #             #     name += ' %s' % upline_dict[agent_type_code]
    #             upline.write({
    #                 'name': name
    #             })
    #         rec.upline_name = ''

    def get_data(self):
        res = {
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
            'commission': {
                'agent': {
                    'commission_by_percentage': {
                        'percentage': self.commission_percentage,
                        'minimum': self.commission_minimum
                    },
                    'commission_by_amount': {
                        'amount': self.commission_amount,
                        'is_route': self.commission_route,
                        'is_segment': self.commission_segment,
                        'is_pax': self.commission_pax,
                        'is_infant': self.commission_infant,
                    },
                },
                'parent': {
                    'charge_by_percentage': {
                        'percentage': self.parent_charge_percentage,
                        'minimum': self.parent_charge_minimum,
                    },
                    'charge_by_amount': {
                        'amount': self.parent_charge_amount,
                        'is_route': self.parent_charge_route,
                        'is_segment': self.parent_charge_segment,
                        'is_pax': self.parent_charge_pax,
                        'is_infant': self.parent_charge_infant,
                    }
                },
                'ho': {
                    'charge_by_percentage': {
                        'percentage': self.ho_charge_percentage,
                        'minimum': self.ho_charge_minimum,
                    },
                    'charge_by_amount': {
                        'amount': self.ho_charge_amount,
                        'is_route': self.ho_charge_route,
                        'is_segment': self.ho_charge_segment,
                        'is_pax': self.ho_charge_pax,
                        'is_infant': self.ho_charge_infant,
                    }
                },
                'residual_amount_to': self.residual_amount_to,
                'upline_list': [rec.get_data() for rec in self.upline_ids],
            },
            'ticketing': {
                'sales': {
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
                'sales': {
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
                'sales': {
                    'upsell_by_amount': {
                        'amount': self.tkt_sales_upsell_amount,
                        'is_route': self.tkt_sales_upsell_route,
                        'is_segment': self.tkt_sales_upsell_segment,
                    }
                }
            },
            'state': self.state,
        }
        return res


class AgentPricingUpline(models.Model):
    _name = 'tt.agent.pricing.upline'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Agent Pricing Upline'

    name = fields.Char('Name', compute='_compute_name', store=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    pricing_line_id = fields.Many2one('tt.agent.pricing.line', 'Pricing Line', readonly=1, ondelete='cascade')

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    commission_percentage = fields.Float('Commission (%)', default=0)
    commission_minimum = fields.Float('Commission Minimum', default=0)
    commission_amount = fields.Float('Commission Amount', default=0)
    commission_route = fields.Boolean('Commission Route', default=False)
    commission_segment = fields.Boolean('Commission Segment', default=False)
    commission_pax = fields.Boolean('Commission Pax', default=False)
    commission_infant = fields.Boolean('Commission Include Infant', default=False)

    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)

    @api.depends('agent_type_id')
    def _compute_name(self):
        for rec in self:
            if rec.agent_type_id:
                rec.name = rec.agent_type_id.name
            else:
                rec.name = ''

    def get_data(self):
        res = {
            'agent_type_code': self.agent_type_id.code if self.agent_type_id else '',
            'commission_by_percentage': {
                'percentage': self.commission_percentage,
                'minimum': self.commission_minimum
            },
            'commission_by_amount': {
                'amount': self.commission_amount,
                'is_route': self.commission_route,
                'is_segment': self.commission_segment,
                'is_pax': self.commission_pax,
                'is_infant': self.commission_infant,
            },
            'state': self.state,
        }
        return res
