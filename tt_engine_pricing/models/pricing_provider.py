from odoo import models, fields, api, _
from ...tools import variables


class PricingProvider(models.Model):
    _name = 'tt.pricing.provider'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    pricing_type = fields.Selection([
        ('sale', 'Sale'),
        ('commission', 'Commission'),
    ], 'Pricing Type', required=True)
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_pricing_carrier_rel', 'pricing_id', 'carrier_id',
                                   string='Carriers')
    is_all_carrier = fields.Boolean('Is All Carrier', default=False)
    line_ids = fields.One2many('tt.pricing.provider.line', 'pricing_id', 'Configs')
    active = fields.Boolean('Active', default=True)


class PricingProviderLine(models.Model):
    _name = 'tt.pricing.provider.line'

    name = fields.Char('Name', requried=True)
    sequence = fields.Integer('Sequence', default=50, required=True)
    pricing_id = fields.Many2one('tt.pricing.provider', 'Pricing Provider')
    date_from = fields.Datetime('Date From', required=True)
    date_to = fields.Datetime('Date To', required=True)
    origin_type = fields.Selection(variables.ACCESS_TYPE, 'Origin Type')
    origin_ids = fields.Many2many('tt.destinations', 'tt_pricing_line_origin_rel', 'pricing_line_id', 'origin_id',
                                  string='Origins')
    origin_city_ids = fields.Many2many('res.city', 'tt_pricing_line_origin_city_rel', 'pricing_line_id', 'city_id',
                                       string='Origin Cities')
    origin_country_ids = fields.Many2many('res.country', 'tt_pricing_line_origin_country_rel', 'pricing_line_id', 'country_id',
                                          string='Origin Countries')
    destination_type = fields.Selection(variables.ACCESS_TYPE, 'Destination Type')
    destination_ids = fields.Many2many('tt.destinations', 'tt_pricing_line_destination_rel', 'pricing_line_id', 'destination_id',
                                       string='Destinations')
    destination_city_ids = fields.Many2many('res.city', 'tt_pricing_line_destination_city_rel', 'pricing_line_id', 'city_id',
                                            string='Destination Cities')
    destination_country_ids = fields.Many2many('res.country', 'tt_pricing_line_destination_country_rel', 'pricing_line_id', 'country_id',
                                               string='Destination Countries')
    currency_id = fields.Many2one('res.currency', 'Currency')
    amount_per_route = fields.Float('Ammount per Route')
    amount_per_segment = fields.Float('Amount per Segment')
    amount_per_pax = fields.Float('Amount per Pax')
    basic_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Basic Amount Type', default='percentage')
    basic_amount = fields.Float('Basic Amount', default=0)
    tax_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Tax Amount Type', default='percentage')
    tax_amount = fields.Float('Tax Amount', default=0)
    after_tax_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'After Tax Amount Type', default='percentage')
    after_tax_amount = fields.Float('After Tax Amount', default=0)
    minimum_limit = fields.Monetary('Minimum Limit', default=0)
    minimum_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Minimum Amount Type', default='amount')
    minimum_amount = fields.Monetary('Minimum Amount', default=0)
    upper_limit = fields.Float('Upper Limit', default=0)
    upper_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Upper Amount Type', default='percentage')
    upper_amount = fields.Float('Upper Ammount', default=0)
    active = fields.Boolean('Active', default=True)
