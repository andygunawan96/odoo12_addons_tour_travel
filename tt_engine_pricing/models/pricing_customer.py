from odoo import models, fields, api, _
from ...tools import variables
from ...tools.api import Response
import traceback, logging
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)


class PricingCustomer(models.Model):
    _name = 'tt.pricing.customer'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Pricing Customer'

    name = fields.Char('Name', readonly=1, compute="_compute_name", store=True)
    name_desc = fields.Char('Name Description')
    sequence = fields.Integer('Sequence', default=50, required=True)

    def _get_ho_id_domain(self):
        return [('agent_type_id', '=', self.env.ref('tt_base.agent_type_ho').id)]

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=_get_ho_id_domain, required=False, default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, default=lambda self: self.env.user.agent_id)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id', readonly=True,
                                    store=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    carrier_access_type = fields.Selection(variables.ACCESS_TYPE, 'Carrier Access Type', required=True, default='allow')
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_pricing_customer_carrier_rel', 'pricing_id', 'carrier_id', string='Carriers')
    line_ids = fields.One2many('tt.pricing.customer.line', 'pricing_id', 'Configs', domain=['|', ('active', '=', 1), ('active', '=', 0)])
    active = fields.Boolean('Active', default=True)
    customer_parent_type_ids = fields.Many2many('tt.customer.parent.type', 'pricing_customer_customer_parent_type_rel', 'pricing_id', 'customer_parent_type_id', string='Customer Parent Types')
    customer_parent_type_access_type = fields.Selection(variables.ACCESS_TYPE, 'Customer Parent Type Access Type', required=True, default='all')
    customer_parent_ids = fields.Many2many('tt.customer.parent', 'pricing_customer_customer_parent_rel', 'pricing_id', 'customer_parent_id', string='Customer Parents')
    customer_parent_access_type = fields.Selection(variables.ACCESS_TYPE, 'Customer Parent Access Type', required=True, default='all')

    def do_compute_name(self):
        objs = self.sudo().search([])
        for rec in objs:
            rec._compute_name()

    def do_compute_sequence(self):
        _objs = self.sudo().with_context(active_test=False).search([], order='sequence')
        count = 10
        line_count = 10
        for rec in _objs:
            rec.update({'sequence': count})
            count += 10
            line_objs = self.env['tt.pricing.customer.line'].sudo().with_context(active_test=False).search([('pricing_id', '=', rec.id)], order='sequence')
            for line in line_objs:
                line.update({'sequence': line_count})
                line_count += 10

    @api.multi
    @api.depends('carrier_access_type', 'carrier_ids', 'customer_parent_type_access_type', 'customer_parent_type_ids', 'customer_parent_access_type', 'customer_parent_ids')
    def _compute_name(self):
        field_list = ['carrier', 'customer_parent_type', 'customer_parent']
        for rec in self:
            name_list = []
            for fld in field_list:
                access_type = getattr(rec, '%s_access_type' % fld)
                name_list.append('%s %s' % (access_type.title(), fld.title()))
                if fld != 'customer_parent':
                    if access_type != 'all':
                        obj_ids = getattr(rec, '%s_ids' % fld)
                        code_list = [obj.code for obj in obj_ids]
                        name_list.append(','.join(code_list))
                else:
                    if access_type != 'all':
                        obj_ids = getattr(rec, '%s_ids' % fld)
                        code_list = [str(obj.id) for obj in obj_ids]
                        name_list.append(','.join(code_list))

            rec.name = ' - '.join(name_list)

    @api.multi
    @api.depends('carrier_ids')
    def _compute_display_carriers(self):
        for rec in self:
            res = '%s' % ','.join([carrier.code for carrier in rec.carrier_ids])
            rec.display_carriers = res

    def get_pricing_data(self):
        line_ids = []
        date_now = datetime.now()

        line_ids_obj = self.env['tt.pricing.customer.line'].sudo().with_context(active_test=False).search([('pricing_id', '=', self.id)])

        for rec in line_ids_obj:
            if rec.active and not rec.is_no_expiration and date_now > rec.date_to:
                try:
                    rec.write({'active': False})
                    _logger.info('Inactive line pricing provider due to expired date')
                except:
                    _logger.info('Failed to inactive line pricing provider, %s' % traceback.format_exc())
            line_data = rec.get_pricing_data()
            line_ids.append(line_data)

        carrier_codes = [rec.code for rec in self.carrier_ids]
        customer_parent_types = [rec.code for rec in self.customer_parent_type_ids]
        customer_parent_ids = [rec.id for rec in self.customer_parent_ids]
        res = {
            'id': self.id,
            'agent_id': self.agent_id and self.agent_id.id or 0,
            'agent_type_code': self.agent_type_id and self.agent_type_id.code or '',
            'provider_type': self.provider_type_id and self.provider_type_id.code or '',
            'carrier_access_type': self.carrier_access_type,
            'carrier_codes': carrier_codes,
            'customer_parent_type_access_type': self.customer_parent_type_access_type,
            'customer_parent_types': customer_parent_types,
            'customer_parent_access_type': self.customer_parent_access_type,
            'customer_parent_ids': customer_parent_ids,
            'line_ids': line_ids
        }
        return res

    def get_pricing_customer_api(self, provider_type):
        try:
            provider_type_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            if not provider_type_obj:
                raise Exception('Provider Type not found, %s' % provider_type)

            _obj = self.sudo().search([('provider_type_id', '=', provider_type_obj.id), ('active', '=', 1)])

            qs = [rec.get_pricing_data() for rec in _obj if rec.active]

            response = {
                'pricing_customers': qs,
                'provider_type': provider_type
            }
            res = Response().get_no_error(response)
        except Exception as e:
            err_msg = '%s, %s' % (str(e), traceback.format_exc())
            res = Response().get_error(err_msg, 500)
        return res


class PricingProviderLine(models.Model):
    _name = 'tt.pricing.customer.line'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Pricing Provider Line'

    name = fields.Char('Name', requried=True)
    sequence = fields.Integer('Sequence', default=50, required=True)
    pricing_id = fields.Many2one('tt.pricing.customer', 'Pricing Provider', readonly=1, ondelete='cascade')
    date_from = fields.Datetime('Date From', default=datetime.now())
    date_to = fields.Datetime('Date To', default=datetime.now() + timedelta(days=1000))
    origin_type = fields.Selection(variables.ACCESS_TYPE, 'Origin Type', required=True, default='all')
    origin_ids = fields.Many2many('tt.destinations', 'tt_pricing_customer_line_origin_rel', 'pricing_line_id', 'origin_id',
                                  string='Origins')
    display_origins = fields.Char('Display Origins', compute='_compute_display_origins', store=True, readonly=1)
    origin_city_ids = fields.Many2many('res.city', 'tt_pricing_customer_line_origin_city_rel', 'pricing_line_id', 'city_id',
                                       string='Origin Cities')
    display_origin_cities = fields.Char('Display Origin Cities', compute='_compute_display_origin_cities', store=True, readonly=1)
    origin_country_ids = fields.Many2many('res.country', 'tt_pricing_customer_line_origin_country_rel', 'pricing_line_id', 'country_id', string='Origin Countries')
    display_origin_countries = fields.Char('Display Origin Countries', compute='_compute_display_origin_countries', store=True, readonly=1)
    destination_type = fields.Selection(variables.ACCESS_TYPE, 'Destination Type', required=True, default='all')
    destination_ids = fields.Many2many('tt.destinations', 'tt_pricing_customer_line_destination_rel', 'pricing_line_id', 'destination_id', string='Destinations')
    display_destinations = fields.Char('Display Destinations', compute='_compute_display_destinations', store=True, readonly=1)
    destination_city_ids = fields.Many2many('res.city', 'tt_pricing_customer_line_destination_city_rel', 'pricing_line_id', 'city_id',
                                            string='Destination Cities')
    display_destination_cities = fields.Char('Display Destination Cities', compute='_compute_display_destination_cities', store=True, readonly=1)

    destination_country_ids = fields.Many2many('res.country', 'tt_pricing_customer_line_destination_country_rel', 'pricing_line_id', 'country_id',
                                               string='Destination Countries')
    display_destination_countries = fields.Char('Display Destination Countries', compute='_compute_display_destination_countries', store=True, readonly=1)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    fee_amount = fields.Monetary('Fee Amount', default=0)
    is_per_route = fields.Boolean('Is Per Route', default=False)
    is_per_segment = fields.Boolean('Is Per Segment', default=False)
    is_per_pax = fields.Boolean('Is Per Pax', default=False)
    upsell_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Upsell Amount Type', default='percentage')
    upsell_amount = fields.Float('Upsell Amount', default=0)
    is_no_expiration = fields.Boolean('No Expiration', default=False)
    active = fields.Boolean('Active', default=True)

    @api.multi
    @api.depends('origin_ids')
    def _compute_display_origins(self):
        for rec in self:
            res = [data.code for data in rec.origin_ids]
            rec.display_origins = ','.join(res)

    @api.multi
    @api.depends('destination_ids')
    def _compute_display_destinations(self):
        for rec in self:
            res = [data.code for data in rec.destination_ids]
            rec.display_destinations = ','.join(res)

    @api.multi
    @api.depends('origin_city_ids')
    def _compute_display_origin_cities(self):
        for rec in self:
            res = [data.code for data in rec.origin_city_ids]
            rec.display_origin_cities = ','.join(res)

    @api.multi
    @api.depends('destination_city_ids')
    def _compute_display_destination_cities(self):
        for rec in self:
            res = [data.code for data in rec.destination_city_ids]
            rec.display_destination_cities = ','.join(res)

    @api.multi
    @api.depends('origin_country_ids')
    def _compute_display_origin_countries(self):
        for rec in self:
            res = [data.code for data in rec.origin_country_ids]
            rec.display_origin_countries = ','.join(res)

    @api.multi
    @api.depends('destination_country_ids')
    def _compute_display_destination_countries(self):
        for rec in self:
            res = [data.code for data in rec.destination_country_ids]
            rec.display_destination_countries = ','.join(res)

    def get_pricing_data(self):
        origin_codes = [rec.code for rec in self.origin_ids]
        origin_city_ids = [rec.id for rec in self.origin_city_ids]
        origin_country_codes = [rec.code for rec in self.origin_country_ids]
        destination_codes = [rec.code for rec in self.destination_ids]
        destination_city_ids = [rec.id for rec in self.destination_city_ids]
        destination_country_codes = [rec.code for rec in self.destination_country_ids]
        res = {
            'id': self.id,
            'sequence': self.sequence,
            'date_from': self.date_from.strftime('%Y-%m-%d %H:%M:%S'),
            'date_to': self.date_to.strftime('%Y-%m-%d %H:%M:%S'),
            'origin_type': self.origin_type,
            'origin_codes': origin_codes,
            'origin_city_ids': origin_city_ids,
            'origin_country_codes': origin_country_codes,
            'destination_type': self.destination_type,
            'destination_codes': destination_codes,
            'destination_city_ids': destination_city_ids,
            'destination_country_codes': destination_country_codes,
            'currency_code': self.currency_id and self.currency_id.name or '',
            'fee_amount': self.fee_amount,
            'is_per_route': self.is_per_route,
            'is_per_segment': self.is_per_segment,
            'is_per_pax': self.is_per_pax,
            'upsell_amount_type': self.upsell_amount_type,
            'upsell_amount': self.upsell_amount,
            'is_no_expiration': self.is_no_expiration,
            'active': self.active,
            # 'is_provide_infant_commission': self.is_provide_infant_commission,
        }
        return res

