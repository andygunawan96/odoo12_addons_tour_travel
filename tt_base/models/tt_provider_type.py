from odoo import models, fields, api
from ...tools import variables


class ProviderType(models.Model):
    _name = 'tt.provider.type'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)

    def fill_provider_type(self):
        provider_type_obj = self.search([])
        for rec in provider_type_obj:
            variables.PROVIDER_TYPE.append(rec.code)

    def _register_hook(self):
        self.fill_provider_type()
        print(variables.PROVIDER_TYPE)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
        }
        return res
