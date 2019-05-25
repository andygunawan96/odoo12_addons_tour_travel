from odoo import models, fields, api, _


class ProviderType(models.Model):
    _name = 'tt.provider.type'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
        }
        return res