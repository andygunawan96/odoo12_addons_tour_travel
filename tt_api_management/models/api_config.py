from odoo import models, fields, api, _
from ...tools import variables


class ApiConfig(models.Model):
    _name = 'tt.api.config'
    _description = 'API Config'

    provider_type_id = fields.Many2one(comodel_name='tt.provider.type', string='Provider Type', required=True)
    active = fields.Boolean(string='Active', default=True)
    credential_id = fields.Many2one(comodel_name='tt.api.credential', string='Credential')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])

    def to_dict(self):
        res = self.provider_type_id.to_dict()
        return res

    def get_credential(self):
        res = {}
        return res

    def get_provider_type_code(self):
        res = self.provider_type_id.code
        return res


class ApiCredentialConfigInherit(models.Model):
    _inherit = 'tt.api.credential'

    config_ids = fields.One2many(comodel_name='tt.api.config', inverse_name='credential_id', string='Configs')

    def to_dict(self):
        res = super(ApiCredentialConfigInherit, self).to_dict()
        config_ids = [rec.to_dict() for rec in self.config_ids if rec.active]
        res.update({
            'config_ids': config_ids
        })
        return res

    def get_credential(self):
        res = super(ApiCredentialConfigInherit, self).get_credential()
        configs = {}
        [configs.update({
            rec.get_provider_type_code(): rec.get_credential()
        }) for rec in self.config_ids if rec.active]
        res.update({
            'configs': configs,
        })
        return res
