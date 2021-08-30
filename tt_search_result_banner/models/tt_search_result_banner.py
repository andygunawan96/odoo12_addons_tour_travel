from odoo import api, fields, models
from ...tools.api import Response
import traceback,logging
from ...tools import ERR
import json

_logger = logging.getLogger(__name__)


class SearchResultBanner(models.Model):
    _name = 'tt.search.result.banner'
    _inherit = 'tt.history'
    _description = 'Search Result Banner'

    name = fields.Char('Banner Text', required=True)
    banner_color = fields.Char('Banner Color (Hex Code)', default='#FFFFFF')
    minimum_days = fields.Integer('Minimum Days', default=0)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    provider_id = fields.Many2one('tt.provider', 'Provider', required=True, domain="[('provider_type_id', '=', provider_type_id)]")
    carrier_id = fields.Many2one('tt.transport.carrier', 'Product', required=True, domain="[('provider_type_id', '=', provider_type_id)]")
    active = fields.Boolean('Active', default=True)

    @api.onchange('provider_type_id')
    def _onchange_domain_provider(self):
        self.provider_id = False
        self.carrier_id = False
        return {'domain': {
            'provider_id': [('provider_type_id', '=', self.provider_type_id.id)],
            'carrier_id': [('provider_type_id', '=', self.provider_type_id.id)]
        }}
