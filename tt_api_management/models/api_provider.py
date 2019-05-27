from odoo import models, fields, api, _
from ...tools import variables


class ApiProvider(models.Model):
    _name = 'tt.api.provider'

    config_id = fields.Many2one(comodel_name='tt.api.config', string='Config')
    provider_id = fields.Many2one(comodel_name='tt.provider', string='Provider', required=1)
    active = fields.Boolean(string='Active', default=True)

    def to_dict(self):
        res = self.provider_id.to_dict()
        return res

    def get_credential(self):
        res = {}
        return res

    def get_provider_code(self):
        res = self.provider_id.code
        return res


class ApiConnectorCarrierInherit(models.Model):
    _inherit = 'tt.api.config'

    provider_access = fields.Selection(selection=variables.ACCESS_TYPE, string='Provider Access', default='all')
    provider_ids = fields.One2many(comodel_name='tt.api.provider', inverse_name='config_id', string='Providers')

    def to_dict(self):
        res = super(ApiConnectorCarrierInherit, self).to_dict()
        provider_ids = [rec.to_dict() for rec in self.provider_ids if rec.active] if self.provider_access != 'all' else []
        res.update({
            'provider_access': self.provider_access,
            'provider_ids': provider_ids
        })
        return res

    def get_credential(self):
        res = super(ApiConnectorCarrierInherit, self).get_credential()
        providers = {}
        [providers.update({
            rec.get_provider_code(): rec.get_credential()
        }) for rec in self.provider_ids if rec.active] if self.provider_access != 'all' else []
        res.update({
            'provider_access': self.provider_access,
            'providers': providers,
        })
        return res
