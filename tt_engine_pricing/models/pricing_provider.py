from odoo import models, fields, api, _
from ...tools import variables
from ...tools.api import Response
import traceback


class PricingProvider(models.Model):
    _name = 'tt.pricing.provider'

    name = fields.Char('Name', readonly=1)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    provider_id = fields.Many2one('tt.provider', 'Provider', required=True)
    pricing_type = fields.Selection([
        ('sale', 'Sale'),
        ('commission', 'Commission'),
        ('provider', 'provider'),
    ], 'Pricing Type', required=True)
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_pricing_provider_carrier_rel', 'pricing_id', 'carrier_id', string='Carriers')
    line_ids = fields.One2many('tt.pricing.provider.line', 'pricing_id', 'Configs')
    active = fields.Boolean('Active', default=True)

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        res = '%s (%s) - %s' % (self.provider_id.code.title(), self.pricing_type.title(), ','.join([rec.code for rec in self.carrier_ids]))
        return res

    @api.model
    def create(self, values):
        res = super(PricingProvider, self).create(values)
        res.write({})
        return res

    def write(self, values):
        res = super(PricingProvider, self).write(values)
        if not values.get('name'):
            self.write({'name': self.get_name()})
        return res

    def get_pricing_data(self):
        line_ids = [rec.get_pricing_data() for rec in self.line_ids if rec.active]
        # line_ids = sorted(line_ids, key=lambda i: i['sequence'])
        carrier_codes = [rec.code for rec in self.carrier_ids]
        res = {
            'provider_type': self.provider_type_id and self.provider_type_id.code,
            'provider': self.provider_id and self.provider_id.code,
            'pricing_type': self.pricing_type,
            'carrier_codes': carrier_codes,
            'line_ids': line_ids,
        }
        return res

    def get_pricing_provider_api(self, provider_type):
        try:
            provider_type_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            if not provider_type_obj:
                raise Exception('Provider Type not found, %s' % provider_type)

            _obj = self.sudo().search([('provider_type_id', '=', provider_type_obj.id), ('active', '=', 1)])

            response = {}
            for rec in _obj:
                if not rec.active:
                    continue
                temp = rec.get_pricing_data()
                carrier_codes = temp.pop('carrier_codes')
                provider = rec.provider_id.code
                pricing_type = rec.pricing_type

                if not response.get(provider):
                    response[provider] = {}

                for carrier_code in carrier_codes:
                    if not response[provider].get(carrier_code):
                        response[provider][carrier_code] = {}
                    response[provider][carrier_code].update({
                        pricing_type: temp
                    })
            res = Response().get_no_error(response)
        except Exception as e:
            err_msg = '%s, %s' % (str(e), traceback.format_exc())
            res = Response().get_error(err_msg, 500)
        return res


class PricingProviderLine(models.Model):
    _name = 'tt.pricing.provider.line'
    _order = 'sequence'

    name = fields.Char('Name', requried=True)
    sequence = fields.Integer('Sequence', default=50, required=True)
    pricing_id = fields.Many2one('tt.pricing.provider', 'Pricing Provider', readonly=1)
    date_from = fields.Datetime('Date From', required=True)
    date_to = fields.Datetime('Date To', required=True)
    origin_type = fields.Selection(variables.ACCESS_TYPE, 'Origin Type', required=True, default='all')
    origin_ids = fields.Many2many('tt.destinations', 'tt_pricing_provider_line_origin_rel', 'pricing_line_id', 'origin_id',
                                  string='Origins')
    origin_city_ids = fields.Many2many('res.city', 'tt_pricing_provider_line_origin_city_rel', 'pricing_line_id', 'city_id',
                                       string='Origin Cities')
    origin_country_ids = fields.Many2many('res.country', 'tt_pricing_provider_line_origin_country_rel', 'pricing_line_id', 'country_id',
                                          string='Origin Countries')
    destination_type = fields.Selection(variables.ACCESS_TYPE, 'Destination Type', required=True, default='all')
    destination_ids = fields.Many2many('tt.destinations', 'tt_pricing_provider_line_destination_rel', 'pricing_line_id', 'destination_id',
                                       string='Destinations')
    destination_city_ids = fields.Many2many('res.city', 'tt_pricing_provider_line_destination_city_rel', 'pricing_line_id', 'city_id',
                                            string='Destination Cities')
    destination_country_ids = fields.Many2many('res.country', 'tt_pricing_provider_line_destination_country_rel', 'pricing_line_id', 'country_id',
                                               string='Destination Countries')
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
    upper_margin = fields.Float('Equal Upper Margin', default=0)
    upper_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Upper Amount Type', default='percentage')
    upper_amount = fields.Float('Upper Ammount', default=0)
    active = fields.Boolean('Active', default=True)

    def get_pricing_data(self):
        origin_codes = [rec.code for rec in self.origin_ids]
        origin_city_ids = [rec.id for rec in self.origin_city_ids]
        origin_country_codes = [rec.code for rec in self.origin_country_ids]
        destination_codes = [rec.code for rec in self.destination_ids]
        destination_city_ids = [rec.id for rec in self.destination_city_ids]
        destination_country_codes = [rec.code for rec in self.destination_country_ids]
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
        }
        return res
