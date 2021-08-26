from odoo import api, fields, models, _
from ...tools import variables


class TtProviderAirlinePricingProviderLine(models.Model):
    _name = 'tt.provider.airline.pricing.provider.line'
    _description = 'Provider Airline Pricing Provider Line'

    pricing_provider_line_id = fields.Many2one('tt.pricing.provider.line', 'Pricing Provider Line')
    pricing_provider_id = fields.Many2one('tt.pricing.provider', 'Pricing Provider', related='pricing_provider_line_id.pricing_id')
    provider_id = fields.Many2one('tt.provider.airline', 'Provider Airline', ondelete='cascade')
    pricing_type = fields.Selection([
        ('sale', 'Sale'),
        ('commission', 'Commission'),
    ], 'Pricing Type')
    provider_pricing_type = fields.Selection([
        ('main', 'Main'),
        ('append', 'Append'),
    ], 'Provider Pricing Type')


class TtProviderAirlinePricingAgent(models.Model):
    _name = 'tt.provider.airline.pricing.agent'
    _description = 'Provider Airline Pricing Agent'

    pricing_agent_id = fields.Many2one('tt.pricing.agent', 'Pricing Agent')
    provider_id = fields.Many2one('tt.provider.airline', 'Provider Airline', ondelete='cascade')

