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


class AgentCommission(models.Model):
    _name = 'tt.agent.commission'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Agent Commission'

    name = fields.Char('Name', compute='_compute_name', store=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)

    agent_type_name = fields.Char('Agent Type Name', compute='_compute_agent_type_name', store=True)
    agent_type_access_type = fields.Selection(ACCESS_TYPE, 'Agent Type Access Type', default='allow', required=True)
    agent_type_ids = fields.Many2many('tt.agent.type', 'tt_agent_commission_agent_type_rel', 'pricing_id', 'agent_type_id', string='Agent Types')

    provider_type_name = fields.Char('Provider Type Name', compute='_compute_provider_type_name', store=True)
    provider_type_access_type = fields.Selection(ACCESS_TYPE, 'Provider Type Access Type', default='all', required=True)
    provider_type_ids = fields.Many2many('tt.provider.type', 'tt_agent_commission_provider_type_rel', 'pricing_id', 'provider_type_id', string='Provider Types')

    agent_name = fields.Char('Agent Name', compute='_compute_agent_name', store=True)
    agent_access_type = fields.Selection(ACCESS_TYPE, 'Agent Access Type', default='all', required=True)
    agent_ids = fields.Many2many('tt.agent', 'tt_agent_commission_agent_rel', 'pricing_id',
                                 'agent_id', string='Agents')

    provider_name = fields.Char('Provider Name', compute='_compute_provider_name', store=True)
    provider_access_type = fields.Selection(ACCESS_TYPE, 'Provider Access Type', default='all', required=True)
    provider_ids = fields.Many2many('tt.provider', 'tt_agent_commission_provider_rel', 'pricing_id', 'provider_id',
                                    string='Providers')

    carrier_name = fields.Char('Carrier Name', compute='_compute_carrier_name', store=True)
    carrier_access_type = fields.Selection(ACCESS_TYPE, 'Carrier Access Type', default='all', required=True)
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_agent_commission_carrier_rel', 'pricing_id', 'carrier_id',
                                   string='Carriers')

    line_ids = fields.One2many('tt.agent.commission.line', 'pricing_id', string='Rules', context={'active_test': False}, copy=True)

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id.id)
    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)
    pricing_breakdown = fields.Boolean('Pricing Breakdown', related='ho_id.pricing_breakdown', store=True)

    @api.model
    def create(self, vals):
        res = super(AgentCommission, self).create(vals)
        try:
            data = {
                'code': 9901,
                'title': 'AGENT COMMISSION PRICING',
                'message': 'New agent commission pricing created: %s\nUser: %s\n' % (
                    res.name, self.env.user.name)
            }
            context = {
                "co_ho_id": res.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "agent commission pricing changes" telegram notification: ' + str(e))
        return res

    def write(self, vals):
        super(AgentCommission, self).write(vals)
        try:
            data = {
                'code': 9901,
                'title': 'AGENT COMMISSION PRICING',
                'message': 'Agent commission pricing modified: %s\nUser: %s\n' % (
                    self.name, self.env.user.name)
            }
            context = {
                "co_ho_id": self.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "agent commission pricing changes" telegram notification: ' + str(e))

    @api.depends('agent_type_name', 'provider_type_name', 'agent_name', 'provider_name', 'carrier_name')
    def _compute_name(self):
        for rec in self:
            name_list = []
            if rec.agent_type_name:
                name_list.append('%s' % rec.agent_type_name)
            if rec.agent_name:
                name_list.append('[%s]' % rec.agent_name)
            if rec.provider_type_name:
                name_list.append('[%s]' % rec.provider_type_name)
            if rec.provider_name:
                name_list.append('[%s]' % rec.provider_name)
            if rec.carrier_name:
                name_list.append('[%s]' % rec.carrier_name)

            name = ' '.join(name_list)
            rec.name = name

    @api.depends('agent_type_access_type', 'agent_type_ids')
    def _compute_agent_type_name(self):
        for rec in self:
            name_list = []
            agent_type_name = 'For All Agent Types'
            if rec.agent_type_access_type != 'all':
                for agent_type in rec.agent_type_ids:
                    name_list.append('%s' % agent_type.code)
                agent_type_name = '%s in Agent Type %s' % (rec.agent_type_access_type.title(), ','.join(name_list))
            rec.agent_type_name = agent_type_name

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
        _logger.info(msg)
        return True

    def get_data(self):
        res = {
            'id': self.id,
            'sequence': self.sequence,
            'name': self.name if self.name else '',
            # 'agent_type_code': self.agent_type_id.code if self.agent_type_id else '',
            'agent_type': {
                'access_type': self.agent_type_access_type,
                'agent_type_code_list': [rec.code for rec in self.agent_type_ids]
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
            'agent': {
                'access_type': self.agent_access_type,
                'agent_id_list': [rec.id for rec in self.agent_ids]
            },
            'rule_list': [rec.get_data() for rec in self.line_ids if rec.active],
            'state': self.state,
        }
        return res

    def get_agent_commission_api(self):
        try:
            objs = self.env['tt.agent.commission'].sudo().search([])
            agent_commission_data = {}
            date_now = datetime.now().strftime(FORMAT_DATETIME)
            expired_date = datetime.now() + timedelta(seconds=EXPIRED_SECONDS)
            expired_date = expired_date.strftime(FORMAT_DATETIME)
            for obj in objs:
                if not obj.active:
                    continue
                if obj.ho_id:
                    if str(obj.ho_id.id) not in agent_commission_data:
                        agent_commission_data[str(obj.ho_id.id)] = {
                            "agent_commission_list": []
                        }
                    vals = obj.get_data()
                    # December 23, 2021 - SAM
                    # Update struktur pricing agent

                    # agent_type_code = vals['agent_type_code']
                    # if agent_type_code not in agent_commission_data:
                    #     agent_commission_data[agent_type_code] = {
                    #         'agent_commission_list': [],
                    #         'create_date': date_now,
                    #         'expired_date': expired_date,
                    #     }
                    # agent_commission_data[agent_type_code]['agent_commission_list'].append(vals)
                    agent_commission_data[str(obj.ho_id.id)]['agent_commission_list'].append(vals)

            payload = {
                'agent_commission_data': agent_commission_data
            }
        except Exception as e:
            _logger.error('Error Get Agent Commission Data, %s' % traceback.format_exc())
            payload = {}
        return payload


class AgentCommissionLine(models.Model):
    _name = 'tt.agent.commission.line'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Agent Commission Line'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    pricing_id = fields.Many2one('tt.agent.commission', 'Agent Commission', readonly=1, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', 'Currency', ondelete='cascade')
    set_expiration_date = fields.Boolean('Set Expiration Date', default=False)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')
    pricing_breakdown = fields.Boolean('Pricing Breakdown', related='pricing_id.pricing_breakdown', store=True)

    origin_name = fields.Char('Origin Name')
    origin_access_type = fields.Selection(ACCESS_TYPE, 'Origin Access Type', default='all', required=True)
    origin_ids = fields.Many2many('tt.destinations', 'tt_agent_commission_destinations_origin_rel',
                                  'pricing_line_id', 'destination_id', string='Origin')
    origin_city_ids = fields.Many2many('res.city', 'tt_agent_commission_city_origin_rel',
                                       'pricing_line_id', 'city_id', string='Origin Cities')
    origin_country_ids = fields.Many2many('res.country', 'tt_agent_commission_country_origin_rel',
                                          'pricing_line_id', 'country_id', string='Origin Countries')

    destination_name = fields.Char('Destination Name')
    destination_access_type = fields.Selection(ACCESS_TYPE, 'Destination Access Type', default='all', required=True)
    destination_ids = fields.Many2many('tt.destinations', 'tt_agent_commission_destinations_destination_rel',
                                       'pricing_line_id', 'destination_id', string='Destination')
    destination_city_ids = fields.Many2many('res.city', 'tt_agent_commission_city_destination_rel',
                                            'pricing_line_id', 'city_id', string='Destination Cities')
    destination_country_ids = fields.Many2many('res.country', 'tt_agent_commission_country_destination_rel',
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

    parent_charge_percentage = fields.Float('Parent Charge (%)', default=0)
    parent_charge_minimum = fields.Float('Parent Charge Minimum', default=0)
    parent_charge_has_minimum = fields.Boolean('Has Minimum', default=True)
    parent_charge_maximum = fields.Float('Maximum Amount', default=0)
    parent_charge_has_maximum = fields.Boolean('Has Maximum', default=False)
    parent_charge_amount = fields.Float('Parent Charge Amount', default=0)
    parent_charge_route = fields.Boolean('Parent Charge Route', default=False)
    parent_charge_segment = fields.Boolean('Parent Charge Segment', default=False)
    parent_charge_pax = fields.Boolean('Parent Charge Pax', default=False)
    parent_charge_infant = fields.Boolean('Parent Charge Include Infant', default=False)
    ho_charge_percentage = fields.Float('HO Charge (%)', default=0)
    ho_charge_minimum = fields.Float('HO Charge Minimum', default=0)
    ho_charge_has_minimum = fields.Boolean('Has Minimum', default=True)
    ho_charge_maximum = fields.Float('Maximum Amount', default=0)
    ho_charge_has_maximum = fields.Boolean('Has Maximum', default=False)
    ho_charge_amount = fields.Float('HO Charge Amount', default=0)
    ho_charge_route = fields.Boolean('HO Charge Route', default=False)
    ho_charge_segment = fields.Boolean('HO Charge Segment', default=False)
    ho_charge_pax = fields.Boolean('HO Charge Pax', default=False)
    ho_charge_infant = fields.Boolean('HO Charge Include Infant', default=False)
    commission_percentage = fields.Float('Commission (%)', default=0)
    commission_minimum = fields.Float('Commission Minimum', default=0)
    commission_has_minimum = fields.Boolean('Has Minimum', default=True)
    commission_maximum = fields.Float('Maximum Amount', default=0)
    commission_has_maximum = fields.Boolean('Has Maximum', default=False)
    commission_amount = fields.Float('Commission Amount', default=0)
    commission_route = fields.Boolean('Commission Route', default=False)
    commission_segment = fields.Boolean('Commission Segment', default=False)
    commission_pax = fields.Boolean('Commission Pax', default=False)
    commission_infant = fields.Boolean('Commission Include Infant', default=False)

    discount_percentage = fields.Float('Discount (%)', default=0)
    discount_minimum = fields.Float('Discount Minimum', default=0)
    discount_has_minimum = fields.Boolean('Has Minimum', default=True)
    discount_maximum = fields.Float('Maximum Amount', default=0)
    discount_has_maximum = fields.Boolean('Has Maximum', default=False)
    discount_amount = fields.Float('Discount Amount', default=0)
    discount_route = fields.Boolean('Discount Route', default=False)
    discount_segment = fields.Boolean('Discount Segment', default=False)
    discount_pax = fields.Boolean('Discount Pax', default=False)
    discount_infant = fields.Boolean('Discount Include Infant', default=False)

    upline_name = fields.Char('Upline Name') # , compute='_compute_upline_name'
    upline_ids = fields.One2many('tt.agent.commission.upline', 'pricing_line_id', string='Uplines', context={'active_test': False}, copy=True)
    residual_amount_to = fields.Selection([
        ('ho', 'Head Office'),
        ('parent', 'Parent Agent'),
        ('agent', 'Agent'),
    ], 'Residual Amount To', default='ho')

    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)

    # August 15, 2023 - SAM
    total_name = fields.Char('Amount Name')
    total_access_type = fields.Selection(ACCESS_TYPE_3, 'Amount Access Type', default='all', required=True)
    total_is_less_equal = fields.Boolean('Is Less Equal to', default=False)
    total_less_amount = fields.Float('Less than amount', default=0.0)
    total_is_greater_equal = fields.Boolean('Is Greater Equal to', default=False)
    total_greater_amount = fields.Float('Greater than amount', default=0.0)

    # END

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

    @api.model
    def create(self, vals):
        res = super(AgentCommissionLine, self).create(vals)
        try:
            data = {
                'code': 9901,
                'title': 'AGENT COMMISSION PRICING LINE',
                'message': 'New agent commission pricing line created: %s (%s)\nUser: %s\n' % (
                    res.name, res.pricing_id.name, self.env.user.name)
            }
            context = {
                "co_ho_id": res.pricing_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "agent commission pricing line changes" telegram notification: ' + str(e))
        return res

    def write(self, vals):
        super(AgentCommissionLine, self).write(vals)
        try:
            data = {
                'code': 9901,
                'title': 'AGENT COMMISSION PRICING LINE',
                'message': 'Agent commission pricing line modified: %s (%s)\nUser: %s\n' % (
                    self.name, self.pricing_id.name, self.env.user.name)
            }
            context = {
                "co_ho_id": self.pricing_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "agent commission pricing line changes" telegram notification: ' + str(e))

    def get_data(self):
        res = {
            'id': self.id,
            'sequence': self.sequence,
            'name': self.name if self.name else '',
            'currency_code': self.currency_id.name if self.currency_id else '',
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
                },
                'total': {
                    'access_type': self.total_access_type,
                    'is_less_equal': self.total_is_less_equal,
                    'less_amount': self.total_less_amount,
                    'is_greater_equal': self.total_is_greater_equal,
                    'greater_amount': self.total_greater_amount,
                }
            },
            'commission': {
                'agent': {
                    'commission_by_percentage': {
                        'percentage': self.commission_percentage,
                        'minimum': self.commission_minimum,
                        'has_minimum': self.commission_has_minimum,
                        'maximum': self.commission_maximum,
                        'has_maximum': self.commission_has_maximum,
                    },
                    'commission_by_amount': {
                        'amount': self.commission_amount,
                        'is_route': self.commission_route,
                        'is_segment': self.commission_segment,
                        'is_pax': self.commission_pax,
                        'is_infant': self.commission_infant,
                    },
                    'discount_by_percentage': {
                        'percentage': self.discount_percentage,
                        'minimum': self.discount_minimum,
                        'has_minimum': self.discount_has_minimum,
                        'maximum': self.discount_maximum,
                        'has_maximum': self.discount_has_maximum,
                    },
                    'discount_by_amount': {
                        'amount': self.discount_amount,
                        'is_route': self.discount_route,
                        'is_segment': self.discount_segment,
                        'is_pax': self.discount_pax,
                        'is_infant': self.discount_infant,
                    },
                },
                'parent': {
                    'charge_by_percentage': {
                        'percentage': self.parent_charge_percentage,
                        'minimum': self.parent_charge_minimum,
                        'has_minimum': self.parent_charge_has_minimum,
                        'maximum': self.parent_charge_maximum,
                        'has_maximum': self.parent_charge_has_maximum,
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
                        'has_minimum': self.ho_charge_has_minimum,
                        'maximum': self.ho_charge_maximum,
                        'has_maximum': self.ho_charge_has_maximum,
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
                'upline_list': [rec.get_data() for rec in self.upline_ids if rec.active],
            },
            'pricing_breakdown': self.pricing_breakdown,
            'state': self.state,
        }
        return res


class AgentCommissionUpline(models.Model):
    _name = 'tt.agent.commission.upline'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Agent Commission Upline'

    name = fields.Char('Name', compute='_compute_name', store=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    pricing_line_id = fields.Many2one('tt.agent.commission.line', 'Pricing Line', readonly=1, ondelete='cascade')

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    commission_percentage = fields.Float('Commission (%)', default=0)
    commission_minimum = fields.Float('Commission Minimum', default=0)
    commission_has_minimum = fields.Boolean('Has Minimum', default=True)
    commission_maximum = fields.Float('Commission Maximum', default=0)
    commission_has_maximum = fields.Boolean('Has Maximum', default=False)
    commission_amount = fields.Float('Commission Amount', default=0)
    commission_route = fields.Boolean('Commission Route', default=False)
    commission_segment = fields.Boolean('Commission Segment', default=False)
    commission_pax = fields.Boolean('Commission Pax', default=False)
    commission_infant = fields.Boolean('Commission Include Infant', default=False)

    state = fields.Selection(STATE, 'State', default='enable')
    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals):
        res = super(AgentCommissionUpline, self).create(vals)
        try:
            data = {
                'code': 9901,
                'title': 'AGENT COMMISSION PRICING UPLINE',
                'message': 'New agent commission pricing upline created: %s - %s (%s)\nUser: %s\n' % (
                    res.name, res.pricing_line_id.name, res.pricing_line_id.pricing_id.name, self.env.user.name)
            }
            context = {
                "co_ho_id": res.pricing_line_id.pricing_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "agent commission pricing upline changes" telegram notification: ' + str(e))
        return res

    def write(self, vals):
        super(AgentCommissionUpline, self).write(vals)
        try:
            data = {
                'code': 9901,
                'title': 'AGENT COMMISSION PRICING UPLINE',
                'message': 'Agent commission pricing upline modified: %s - %s (%s)\nUser: %s\n' % (
                    self.name, self.pricing_line_id.name, self.pricing_line_id.pricing_id.name, self.env.user.name)
            }
            context = {
                "co_ho_id": self.pricing_line_id.pricing_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "agent commission pricing upline changes" telegram notification: ' + str(e))

    @api.depends('agent_type_id')
    def _compute_name(self):
        for rec in self:
            if rec.agent_type_id:
                rec.name = rec.agent_type_id.name
            else:
                rec.name = ''

    def get_data(self):
        res = {
            'id': self.id,
            'sequence': self.sequence,
            'agent_type_code': self.agent_type_id.code if self.agent_type_id else '',
            'commission_by_percentage': {
                'percentage': self.commission_percentage,
                'minimum': self.commission_minimum,
                'has_minimum': self.commission_has_minimum,
                'maximum': self.commission_maximum,
                'has_maximum': self.commission_has_maximum,
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
