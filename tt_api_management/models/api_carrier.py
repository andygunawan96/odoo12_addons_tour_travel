from odoo import models, fields, api, _
from ...tools import variables


class ApiCarrier(models.Model):
    _name = 'tt.api.carrier'

    active = fields.Boolean(string='Active', default=True)
    provider_id = fields.Many2one(comodel_name='tt.api.provider', string='Provider')
    carrier_id = fields.Many2one(comodel_name='tt.transport.carrier', string='Carrier', required=1)

    def to_dict(self):
        res = self.carrier_id.to_dict()
        return res

    def get_credential(self):
        res = {}
        return res

    def get_carrier_code(self):
        res = self.carrier_id.code
        return res


class ApiConnectorCarrierInherit(models.Model):
    _inherit = 'tt.api.provider'

    carrier_access = fields.Selection(selection=variables.ACCESS_TYPE, string='Carrier Access', default='all')
    carrier_ids = fields.One2many(comodel_name='tt.api.carrier', inverse_name='provider_id', string='Carriers')

    def to_dict(self):
        res = super(ApiConnectorCarrierInherit, self).to_dict()
        carrier_ids = [rec.to_dict() for rec in self.carrier_ids if rec.active] if self.carrier_access != 'all' else []
        res.update({
            'carrier_access': self.carrier_access,
            'carrier_ids': carrier_ids
        })
        return res

    def get_credential(self):
        res = super(ApiConnectorCarrierInherit, self).get_credential()
        carriers = [rec.get_carrier_code() for rec in self.carrier_ids if rec.active] if self.carrier_access != 'all' else []
        res.update({
            'carrier_access': self.carrier_access,
            'carriers': carriers,
        })
        return res
