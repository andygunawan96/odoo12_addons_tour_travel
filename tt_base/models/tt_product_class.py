from odoo import api, fields, models, _
from ...tools.api import Response
import logging
import traceback


_logger = logging.getLogger(__name__)


class ProductClass(models.Model):
    _name = 'tt.product.class'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    cabin_class_id = fields.Many2one('tt.cabin.class', 'Cabin Class')
    carrier_ids = fields.Many2many('tt.transport.carrier', 'tt_product_class_rel', 'product_class_id', 'carrier_id', string='Carriers')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    ssr_list_ids = fields.Many2many('tt.ssr.list', 'tt_product_class_rel', 'product_class_id', 'ssr_id', string='SSR')
    description = fields.Text('Description', default='', help='will convert to list. use ; as separator for list')

    def to_dict(self):
        carrier_ids = [rec.to_dict() for rec in self.carrier_ids]
        ssr_list_ids = [rec.to_dict() for rec in self.ssr_list_ids]
        res = {
            'name': self.name,
            'code': self.code,
            'cabin_class_id': self.cabin_class_id and self.cabin_class_id.to_dict() or {},
            'description': self.description and self.description or '',
            'carrier_ids': carrier_ids,
            'provider_id': self.provider_id and self.provider_id.to_dict() or {},
            'ssr_list_ids': ssr_list_ids,
        }
        return res

    def get_data(self):
        carriers = [rec.get_carrier_data() for rec in self.carrier_ids]
        ssr_list = [rec.get_ssr_data() for rec in self.ssr_list_ids]
        description = self.description and self.description.split(';') or []
        for desc in description:
            desc = desc.strip()
        res = {
            'name': self.name,
            'code': self.code,
            'cabin_class': self.cabin_class_id and self.cabin_class_id.code or '',
            'description': description,
            'provider': self.provider_id and self.provider_id.get_data() or {},
            'carriers': carriers,
            'ssr_list': ssr_list,
        }
        return res
