from odoo import api, fields, models, _
from ...tools.api import Response
import logging
import traceback

_logger = logging.getLogger(__name__)


class CabinClass(models.Model):
    _name = 'tt.cabin.class'
    _description = 'Cabin Class'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
        }
        return res

    def get_data(self):
        res = {
            'name': self.name,
            'code': self.code,
        }
        return res
