from odoo import models, fields, api, _


class ApiHost(models.Model):
    _name = 'tt.api.host'
    _description = 'API Host'

    ip = fields.Char(string='IP', required=1)
    active = fields.Boolean(string='Active')
    credential_id = fields.Many2one(comodel_name='tt.api.credential', string='Credential')

    def to_dict(self):
        res = {
            'ip': self.ip and self.ip or ''
        }
        return res

    def get_credential(self):
        res = {}
        return res


class ApiCredentialHostInherit(models.Model):
    _inherit = 'tt.api.credential'

    host_ids = fields.One2many(comodel_name='tt.api.host', inverse_name='credential_id', string='Hosts')

    def to_dict(self):
        res = super(ApiCredentialHostInherit, self).to_dict()
        host_ids = [rec.to_dict() for rec in self.host_ids if rec.active]
        res.update({
            'host_ids': host_ids
        })
        return res

    def get_credential(self):
        res = super(ApiCredentialHostInherit, self).get_credential()
        host_ips = [rec.ip for rec in self.host_ids if rec.active]
        res.update({
            'host_ips': host_ips,
        })
        return res
