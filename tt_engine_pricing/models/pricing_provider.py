from odoo import models, fields, api, _


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
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_carrier_pricing_rel', 'pricing_id', 'carrier_id',
                                   string='Carriers')
    is_all_carrier = fields.Boolean('Is All Carrier', default=False)
    active = fields.Boolean('Active', default=True)


class PricingProviderLine(models.Model):
    _name = 'tt.pricing.provider.line'

    name = fields.Char('Name', requried=True)
    sequence = fields.Integer('Sequence')
    date_from = fields.Datetime('Date From', required=True)
    date_to = fields.Datetime('Date To', required=True)
    # origin_type =
    # origin_ids = fields.Many2many('tt.destinations')
    # origin_country_ids = fields.Many2many()
    # destination_type
    # destination_ids
    # destination_country_ids
    # amount_per_route
    # amount_per_segment
    # amount_per_pax
    active = fields.Boolean('Active', default=True)
