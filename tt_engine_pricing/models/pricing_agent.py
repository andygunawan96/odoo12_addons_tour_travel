from odoo import models, fields, api, _


class PricingAgent(models.Model):
    _name = 'tt.pricing.agent'

    name = fields.Char('Name')
