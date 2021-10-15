from odoo import api, fields, models
from ...tools.api import Response
import traceback,logging
from ...tools import ERR
import json

_logger = logging.getLogger(__name__)


class SearchResultBanner(models.Model):
    _name = 'tt.search.result.banner'
    _inherit = 'tt.history'
    _order = 'sequence'
    _description = 'Search Result Banner'

    name = fields.Char('Banner Text', required=True)
    description = fields.Text('Description', default='')
    banner_color = fields.Char('Banner Color (Hex Code)', default='#FF0000', required=True)
    text_color = fields.Char('Text Color (Hex Code)', default='#FFFFFF', required=True)
    minimum_days = fields.Integer('Minimum Days', default=0)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    sector_type = fields.Selection([('all', 'All'), ('domestic', 'Domestic'), ('international', 'International')], 'Sector', default='all', required=True)
    provider_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")], 'Provider Access Type', default='all')
    provider_ids = fields.Many2many('tt.provider', "tt_search_banner_provider_rel", "search_banner_id", "provider_id", "Provider", domain="[('provider_type_id', '=', provider_type_id)]")
    carrier_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")], 'Product Access Type', default='all')
    carrier_ids = fields.Many2many('tt.transport.carrier', "tt_search_banner_carrier_rel", "search_banner_id", "carrier_id", "Product", domain="[('provider_type_id', '=', provider_type_id)]")
    origin_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")], 'Origin Access Type', default='all')
    origin_ids = fields.Many2many('tt.destinations', "tt_search_banner_origin_rel", "search_banner_id", "origin_id", "Origin")
    destination_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")], 'Destination Access Type', default='all')
    destination_ids = fields.Many2many('tt.destinations', "tt_search_banner_destination_rel", "search_banner_id", "destination_id", "Destination")
    sequence = fields.Integer('Sequence', default=50)
    active = fields.Boolean('Active', default=True)

    @api.onchange('provider_type_id')
    def _onchange_domain_provider(self):
        self.provider_id = False
        self.carrier_id = False
        return {'domain': {
            'provider_id': [('provider_type_id', '=', self.provider_type_id.id)],
            'carrier_id': [('provider_type_id', '=', self.provider_type_id.id)]
        }}

    def get_search_banner_api(self):
        try:
            _objs = self.search([])
            # response = [rec.get_ssr_data() for rec in _objs]
            ssrs = [rec.get_search_banner_data() for rec in _objs]
            response = {
                'search_banner_data': ssrs,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get SSR API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_search_banner_data(self):
        provider_list = [{
            'name': rec.name,
            'code': rec.code
        } for rec in self.provider_ids]
        carrier_list = [{
            'name': rec.name,
            'code': rec.code
        } for rec in self.carrier_ids]
        origin_list = [{
            'name': rec.name,
            'code': rec.code
        } for rec in self.origin_ids]
        destination_list = [{
            'name': rec.name,
            'code': rec.code
        } for rec in self.destination_ids]
        res = {
            'name': self.name,
            'description': self.description,
            'banner_color': self.banner_color,
            'text_color': self.text_color,
            'minimum_days': self.minimum_days and self.minimum_days or '',
            'provider_type_id': self.provider_type_id and self.provider_type_id.code or '',
            'sector_type': self.sector_type,
            'provider_access_type': self.provider_access_type or 'all',
            'provider_ids': provider_list,
            'carrier_access_type': self.carrier_access_type or 'all',
            'carrier_ids': carrier_list,
            'origin_access_type': self.origin_access_type or 'all',
            'origin_ids': origin_list,
            'destination_access_type': self.destination_access_type or 'all',
            'destination_ids': destination_list,
            'sequence': self.sequence,
            'active': self.active,
        }
        return res
