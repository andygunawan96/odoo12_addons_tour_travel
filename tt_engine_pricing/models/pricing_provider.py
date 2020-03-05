from odoo import models, fields, api, _
from ...tools import variables
from ...tools.api import Response
import traceback, logging
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)


class PricingProvider(models.Model):
    _name = 'tt.pricing.provider'
    _order = 'sequence'
    _description = 'Rodex Model'

    name = fields.Char('Name', readonly=1, compute="_compute_name", store=True)
    sequence = fields.Integer('Sequence', default=50, required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    provider_access_type = fields.Selection(variables.ACCESS_TYPE, 'Provider Access Type', required=True, default='allow')
    provider_ids = fields.Many2many('tt.provider', 'pricing_provider_rel', 'pricing_id', 'provider_id', 'Providers')
    carrier_access_type = fields.Selection(variables.ACCESS_TYPE, 'Carrier Access Type', required=True, default='allow')
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_pricing_provider_carrier_rel', 'pricing_id', 'carrier_id', string='Carriers')
    line_ids = fields.One2many('tt.pricing.provider.line', 'pricing_id', 'Configs', domain=['|', ('active', '=', 1), ('active', '=', 0)])
    active = fields.Boolean('Active', default=True)
    is_sale = fields.Boolean('Is Sale', default=False)
    is_commission = fields.Boolean('Is Commission', default=False)
    is_provider_commission = fields.Boolean('Is Provider Commission', default=False)

    def do_compute_name(self):
        objs = self.sudo().search([])
        for rec in objs:
            rec._compute_name()

    @api.multi
    @api.depends('provider_ids.code','provider_ids','carrier_ids','carrier_ids.code')
    def _compute_name(self):
        for rec in self:
            res = '%s - %s' % (','.join([provider.code.title() for provider in rec.provider_ids]), ','.join([carrier.code for carrier in rec.carrier_ids]))
            rec.name = res

    @api.multi
    @api.depends('provider_ids')
    def _compute_display_providers(self):
        for rec in self:
            res = '%s' % ','.join([provider.code.title() for provider in rec.provider_ids])
            rec.display_providers = res

    @api.multi
    @api.depends('carrier_ids')
    def _compute_display_carriers(self):
        for rec in self:
            res = '%s' % ','.join([carrier.code for carrier in rec.carrier_ids])
            rec.display_carriers = res

    # @api.model
    # def create(self, values):
    #     res = super(PricingProvider, self).create(values)
    #     return res
    #
    # def write(self, values):
    #     res = super(PricingProvider, self).write(values)
    #     return res

    def get_pricing_data(self):
        # February 11, 2020 - SAM
        # Update mekanisme auto inactive untuk data yang expired
        # line_ids = [rec.get_pricing_data() for rec in self.line_ids if rec.active]
        line_ids = []
        date_now = datetime.now()

        # for rec in self.line_ids:
        #     if not rec.active:
        #         continue
        #     if not rec.is_no_expiration and date_now > rec.date_to:
        #         try:
        #             rec.write({'active': False})
        #             _logger.info('Inactive line pricing provider due to expired date')
        #         except:
        #             _logger.info('Failed to inactive line pricing provider, %s' % traceback.format_exc())
        #         continue
        #     line_data = rec.get_pricing_data()
        #     line_ids.append(line_data)

        line_ids_obj = self.env['tt.pricing.provider.line'].sudo().with_context(active_test=False).search([('pricing_id', '=', self.id)])

        for rec in line_ids_obj:
            if rec.active and not rec.is_no_expiration and date_now > rec.date_to:
                try:
                    rec.write({'active': False})
                    _logger.info('Inactive line pricing provider due to expired date')
                except:
                    _logger.info('Failed to inactive line pricing provider, %s' % traceback.format_exc())
            line_data = rec.get_pricing_data()
            line_ids.append(line_data)

        # line_ids = sorted(line_ids, key=lambda i: i['sequence'])
        carrier_codes = [rec.code for rec in self.carrier_ids]
        providers = [rec.code for rec in self.provider_ids]
        res = {
            'provider_type': self.provider_type_id and self.provider_type_id.code or '',
            # 'provider': self.provider_id and self.provider_id.code,
            'provider_access_type': self.provider_access_type,
            'providers': providers,
            # 'pricing_type': self.pricing_type,
            'carrier_access_type': self.carrier_access_type,
            'carrier_codes': carrier_codes,
            'is_sale': self.is_sale,
            'is_commission': self.is_commission,
            'is_provider_commission': self.is_provider_commission,
            'line_ids': line_ids,
        }
        return res

    def get_pricing_provider_api(self, provider_type):
        try:
            provider_type_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            if not provider_type_obj:
                raise Exception('Provider Type not found, %s' % provider_type)

            _obj = self.sudo().search([('provider_type_id', '=', provider_type_obj.id), ('active', '=', 1)])

            qs = [rec.get_pricing_data() for rec in _obj if rec.active]

            # response = {}
            # for rec in _obj:
            #     if not rec.active:
            #         continue
            #     temp = rec.get_pricing_data()
            #     carrier_codes = temp.pop('carrier_codes')
            #     providers = temp.pop('providers')
            #     is_sale = temp.get('is_sale')
            #     is_commission = temp.get('is_commission')
            #     is_provider_commission = temp.get('is_provider_commission')
            #
            #     for provider in providers:
            #         if not response.get(provider):
            #             response[provider] = {}
            #
            #         for carrier_code in carrier_codes:
            #             if not response[provider].get(carrier_code):
            #                 response[provider][carrier_code] = {}
            #             if is_sale:
            #                 response[provider][carrier_code].update({
            #                     'sale': temp
            #                 })
            #             if is_commission:
            #                 response[provider][carrier_code].update({
            #                     'commission': temp
            #                 })
            #             if is_provider_commission:
            #                 response[provider][carrier_code].update({
            #                     'provider': temp
            #                 })

            response = {
                'pricing_providers': qs,
                'provider_type': provider_type
            }
            res = Response().get_no_error(response)
        except Exception as e:
            err_msg = '%s, %s' % (str(e), traceback.format_exc())
            res = Response().get_error(err_msg, 500)
        return res


class PricingProviderLine(models.Model):
    _name = 'tt.pricing.provider.line'
    _order = 'sequence'
    _description = 'Rodex Model'

    name = fields.Char('Name', requried=True)
    sequence = fields.Integer('Sequence', default=50, required=True)
    pricing_id = fields.Many2one('tt.pricing.provider', 'Pricing Provider', readonly=1)
    date_from = fields.Datetime('Date From', default=datetime.now())
    date_to = fields.Datetime('Date To', default=datetime.now() + timedelta(days=1000))
    origin_type = fields.Selection(variables.ACCESS_TYPE, 'Origin Type', required=True, default='all')
    origin_ids = fields.Many2many('tt.destinations', 'tt_pricing_provider_line_origin_rel', 'pricing_line_id', 'origin_id',
                                  string='Origins')
    display_origins = fields.Char('Display Origins', compute='_compute_display_origins', store=True, readonly=1)
    origin_city_ids = fields.Many2many('res.city', 'tt_pricing_provider_line_origin_city_rel', 'pricing_line_id', 'city_id',
                                       string='Origin Cities')
    display_origin_cities = fields.Char('Display Origin Cities', compute='_compute_display_origin_cities', store=True, readonly=1)
    origin_country_ids = fields.Many2many('res.country', 'tt_pricing_provider_line_origin_country_rel', 'pricing_line_id', 'country_id', string='Origin Countries')
    display_origin_countries = fields.Char('Display Origin Countries', compute='_compute_display_origin_countries', store=True, readonly=1)
    destination_type = fields.Selection(variables.ACCESS_TYPE, 'Destination Type', required=True, default='all')
    destination_ids = fields.Many2many('tt.destinations', 'tt_pricing_provider_line_destination_rel', 'pricing_line_id', 'destination_id', string='Destinations')
    display_destinations = fields.Char('Display Destinations', compute='_compute_display_destinations', store=True, readonly=1)
    destination_city_ids = fields.Many2many('res.city', 'tt_pricing_provider_line_destination_city_rel', 'pricing_line_id', 'city_id',
                                            string='Destination Cities')
    display_destination_cities = fields.Char('Display Destination Cities', compute='_compute_display_destination_cities', store=True, readonly=1)

    destination_country_ids = fields.Many2many('res.country', 'tt_pricing_provider_line_destination_country_rel', 'pricing_line_id', 'country_id',
                                               string='Destination Countries')
    display_destination_countries = fields.Char('Display Destination Countries', compute='_compute_display_destination_countries', store=True, readonly=1)
    charge_code_type = fields.Selection(variables.ACCESS_TYPE, 'Charge Code Type', required=True, default='all')
    charge_code_ids = fields.Many2many('tt.pricing.charge.code', 'tt_pricing_provider_line_charge_code_rel', 'pricing_line_id', 'charge_code_id', string='Charge Codes')
    display_charge_codes = fields.Char('Charge Codes', compute='_compute_display_charge_codes', store=True, readonly=1)
    class_of_service_type = fields.Selection(variables.ACCESS_TYPE, 'Class of Service Type', required=True, default='all')
    class_of_service_ids = fields.Many2many('tt.pricing.class.of.service', 'tt_pricing_provider_line_class_of_service_rel','pricing_line_id', 'class_of_service_id', string='Class of Services')
    display_class_of_services = fields.Char('Class of Services', compute='_compute_display_class_of_services', store=True, readonly=1)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    fee_amount = fields.Monetary('Fee Amount', default=0)
    is_per_route = fields.Boolean('Is Per Route', default=False)
    is_per_segment = fields.Boolean('Is Per Segment', default=False)
    is_per_pax = fields.Boolean('Is Per Pax', default=False)
    basic_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Basic Amount Type', default='percentage')
    basic_amount = fields.Float('Basic Amount', default=0)
    tax_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Tax Amount Type', default='percentage')
    tax_amount = fields.Float('Tax Amount', default=0)
    after_tax_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'After Tax Amount Type', default='percentage')
    after_tax_amount = fields.Float('After Tax Amount', default=0)
    lower_margin = fields.Monetary('Lower Margin', default=0)
    lower_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Lower Amount Type', default='amount')
    lower_amount = fields.Monetary('Lower Amount', default=0)
    upper_margin = fields.Monetary('Equal Upper Margin', default=0)
    upper_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Upper Amount Type', default='percentage')
    upper_amount = fields.Float('Upper Ammount', default=0)
    is_compute_infant_basic = fields.Boolean('Compute Inf Basic Amount', default=False)
    is_compute_infant_tax = fields.Boolean('Compute Inf Tax Amount', default=False)
    is_compute_infant_after_tax = fields.Boolean('Compute Inf After Tax Amount', default=True)
    is_compute_infant_upsell = fields.Boolean('Compute Inf Upsell Amount', default=False)
    is_compute_infant_fee = fields.Boolean('Compute Inf Fee Amount', default=False)
    is_no_expiration = fields.Boolean('No Expiration', default=False)
    # is_provide_infant_commission = fields.Boolean('Provider Infant Commission', default=False)
    active = fields.Boolean('Active', default=True)
    provider_commission_amount = fields.Float('Provider Commission Amount', default=0)

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

    @api.multi
    @api.depends('charge_code_ids')
    def _compute_display_charge_codes(self):
        for rec in self:
            res = [data.code for data in rec.charge_code_ids]
            rec.display_charge_codes = ','.join(res)

    @api.multi
    @api.depends('class_of_service_ids')
    def _compute_display_class_of_services(self):
        for rec in self:
            res = [data.code for data in rec.class_of_service_ids]
            rec.display_class_of_services = ','.join(res)

    def get_pricing_data(self):
        origin_codes = [rec.code for rec in self.origin_ids]
        origin_city_ids = [rec.id for rec in self.origin_city_ids]
        origin_country_codes = [rec.code for rec in self.origin_country_ids]
        destination_codes = [rec.code for rec in self.destination_ids]
        destination_city_ids = [rec.id for rec in self.destination_city_ids]
        destination_country_codes = [rec.code for rec in self.destination_country_ids]
        charge_codes = [rec.code for rec in self.charge_code_ids]
        class_of_services = [rec.code for rec in self.class_of_service_ids]
        res = {
            'sequence': self.sequence,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'origin_type': self.origin_type,
            'origin_codes': origin_codes,
            'origin_city_ids': origin_city_ids,
            'origin_country_codes': origin_country_codes,
            'destination_type': self.destination_type,
            'destination_codes': destination_codes,
            'destination_city_ids': destination_city_ids,
            'destination_country_codes': destination_country_codes,
            'charge_code_type': self.charge_code_type,
            'charge_codes': charge_codes,
            'class_of_service_type': self.class_of_service_type,
            'class_of_services': class_of_services,
            'currency_code': self.currency_id and self.currency_id.name or '',
            'fee_amount': self.fee_amount,
            'is_per_route': self.is_per_route,
            'is_per_segment': self.is_per_segment,
            'is_per_pax': self.is_per_pax,
            'basic_amount_type': self.basic_amount_type,
            'basic_amount': self.basic_amount,
            'tax_amount_type': self.tax_amount_type,
            'tax_amount': self.tax_amount,
            'after_tax_amount_type': self.after_tax_amount_type,
            'after_tax_amount': self.after_tax_amount,
            'lower_margin': self.lower_margin,
            'lower_amount_type': self.lower_amount_type,
            'lower_amount': self.lower_amount,
            'upper_margin': self.upper_margin,
            'upper_amount_type': self.upper_amount_type,
            'upper_amount': self.upper_amount,
            'provider_commission_amount': self.provider_commission_amount,
            'is_compute_infant_basic': self.is_compute_infant_basic,
            'is_compute_infant_tax': self.is_compute_infant_tax,
            'is_compute_infant_after_tax': self.is_compute_infant_after_tax,
            'is_compute_infant_upsell': self.is_compute_infant_upsell,
            'is_compute_infant_fee': self.is_compute_infant_fee,
            'is_no_expiration': self.is_no_expiration,
            'active': self.active,
            # 'is_provide_infant_commission': self.is_provide_infant_commission,
        }
        return res


class PricingChargeCode(models.Model):
    _name = 'tt.pricing.charge.code'
    _description = 'Rodex Model'

    name = fields.Char('Name')
    code = fields.Char('Code', required=True)
    active = fields.Boolean('Active', default=True)

    def get_pricing_data(self):
        res = {
            'name': self.name,
            'code': self.code,
            'active': self.active,
        }
        return res


class PricingClassOfService(models.Model):
    _name = 'tt.pricing.class.of.service'
    _description = 'Rodex Model'

    name = fields.Char('Name')
    code = fields.Char('Code', required=True)
    active = fields.Boolean('Active', default=True)

    def get_pricing_data(self):
        res = {
            'name': self.name,
            'code': self.code,
            'active': self.active,
        }
        return res
