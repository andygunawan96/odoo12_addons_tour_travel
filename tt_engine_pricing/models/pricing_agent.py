from odoo import models, fields, api, _
from ...tools import variables


class PricingAgent(models.Model):
    _name = 'tt.pricing.agent'

    name = fields.Char('Name')
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    line_ids = fields.One2many('tt.pricing.agent.line', 'pricing_id', 'Pricing')
    active = fields.Boolean('Active', default=True)

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        res = '%s' % self.agent_type_id.code.title()
        return res

    @api.model
    def create(self, values):
        res = super(PricingAgent, self).create(values)
        res.write({})
        return res

    def write(self, values):
        values.update({
            'name': self.get_name()
        })
        return super(PricingAgent, self).write(values)


class PricingAgentLine(models.Model):
    _name = 'tt.pricing.agent.line'

    name = fields.Char('Name')
    pricing_id = fields.Many2one('tt.pricing.agent', 'Pricing', readonly=True)
    level = fields.Integer('Agent Level', required=True)
    basic_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Basic Amount Type', default='percentage')
    basic_amount = fields.Float('Basic Amount', default=0)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    fee_amount_per_route = fields.Monetary('Fee Amount per Route', default=0)
    fee_amount_per_segment = fields.Monetary('Fee Amount per Segment', default=0)
    fee_amount_per_pax = fields.Monetary('Fee Amount per Pax', default=0)
    active = fields.Boolean('Active', default=True)

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        res = '%s - Level %s' % (self.pricing_id.name, self.level)
        return res

    @api.model
    def create(self, values):
        res = super(PricingAgentLine, self).create(values)
        res.write({})
        return res

    def write(self, values):
        values.update({
            'name': self.get_name()
        })
        return super(PricingAgentLine, self).write(values)
