from odoo import api, fields, models, _
from ...tools.api import Response
import logging
import traceback
from ...tools.db_connector import GatewayConnector


_logger = logging.getLogger(__name__)
_gw_con = GatewayConnector()


class FareRules(models.Model):
    _name = 'tt.fare.rules'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_product_class_rel', 'product_class_id', 'carrier_id', string='Carriers')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    description = fields.Text('Description', default='', help='will convert to list. use ; as separator for list')

    def to_dict(self):
        carrier_ids = [rec.to_dict() for rec in self.carrier_ids]
        res = {
            'name': self.name,
            'description': self.description and self.description or '',
            'carrier_ids': carrier_ids,
            'provider_id': self.provider_id and self.provider_id.to_dict() or {},
        }
        return res

    def get_data(self):
        carriers = [rec.get_carrier_data() for rec in self.carrier_ids]
        description = self.description and self.description.split(';') or []
        for desc in description:
            desc = desc.strip()
        res = {
            'name': self.name,
            'description': description,
            'provider': self.provider_id and self.provider_id.get_data() or {},
            'carriers': carriers,
        }
        return res
