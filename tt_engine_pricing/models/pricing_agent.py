from odoo import models, fields, api, _
from ...tools import variables
from ...tools.api import Response
import logging, traceback


_logger = logging.getLogger(__name__)


class PricingAgent(models.Model):
    _name = 'tt.pricing.agent'

    name = fields.Char('Name', readonly=1)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    provider_ids = fields.Many2many('tt.provider', 'tt_pricing_agent_provider_rel', 'pricing_id', 'provider_id',
                                    string='Providers')
    basic_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Basic Amount Type', default='percentage')
    basic_amount = fields.Float('Basic Amount', default=0)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    fee_amount = fields.Monetary('Fee Amount', default=False)
    is_per_route = fields.Boolean('Is per Route', default=False)
    is_per_segment = fields.Boolean('Is per Segment', default=False)
    is_per_pax = fields.Boolean('is per Pax', default=0)
    loop_level = fields.Integer('Loop Level', default=0)
    line_ids = fields.One2many('tt.pricing.agent.line', 'pricing_id', 'Pricing')
    active = fields.Boolean('Active', default=True)

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        res = '%s - %s' % (self.agent_type_id.code.title(), self.provider_type_id.code.title())
        return res

    @api.model
    def create(self, values):
        res = super(PricingAgent, self).create(values)
        res.write({})
        return res

    def write(self, values):
        res = super(PricingAgent, self).write(values)
        if not values.get('name'):
            self.write({'name': self.get_name()})
        return res

    def get_pricing_agent_api(self, _provider_type):
        try:
            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
            if not provider_obj:
                raise Exception('Provider Type not found')
            _obj = self.sudo().search([('provider_type_id', '=', provider_obj.id), ('active', '=', 1)])
            response = {}
            for rec in _obj:
                response.update({
                    rec.agent_type_id.code: rec.get_data()
                })
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('%s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_data(self):
        line_dict = {}
        line_ids = []
        [line_dict.update({rec.agent_type_id.code: rec.get_data()}) for rec in self.line_ids if rec.active]
        provider_ids = [rec.code for rec in self.provider_ids]
        res = {
            'agent_type_id': self.agent_type_id.get_data(),
            'provider_type': self.provider_type_id and self.provider_type_id.code or '',
            'provider_ids': provider_ids,
            'basic_amount_type': self.basic_amount_type,
            'basic_amount': self.basic_amount,
            'currency': self.currency_id and self.currency_id.name,
            'fee_amount': self.fee_amount,
            'is_per_route': self.is_per_route,
            'is_per_segment': self.is_per_segment,
            'is_per_pax': self.is_per_pax,
            'loop_level': self.loop_level,
            # 'line_ids': line_ids,
            'line_dict': line_dict,
        }
        return res


class PricingAgentLine(models.Model):
    _name = 'tt.pricing.agent.line'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    pricing_id = fields.Many2one('tt.pricing.agent', 'Pricing', readonly=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    basic_amount_type = fields.Selection(variables.AMOUNT_TYPE, 'Basic Amount Type', default='percentage')
    basic_amount = fields.Float('Basic Amount', default=0)
    active = fields.Boolean('Active', default=True)

    def get_name(self):
        # Perlu diupdate lagi, sementara menggunakan ini
        res = '%s - Level %s' % (self.pricing_id.name, self.level)
        return res

    @api.model
    def create(self, values):
        res = super(PricingAgentLine, self).create(values)
        return res

    def write(self, values):
        return super(PricingAgentLine, self).write(values)

    def get_data(self):
        res = {
            'sequence': self.sequence,
            'agent_type_id': self.agent_type_id.get_data(),
            'basic_amount_type': self.basic_amount_type,
            'basic_amount': self.basic_amount,
        }
        return res
