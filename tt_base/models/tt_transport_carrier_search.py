from odoo import api, fields, models
import logging
import traceback
import json
from ...tools import ERR

_logger = logging.getLogger(__name__)

class TransportCarrier(models.Model):
    _name = 'tt.transport.carrier.search'
    _description = "List of Search Carrier Code"
    _rec_name = 'name'
    _order = 'is_favorite desc,sequence,name'

    name = fields.Char("Search Display")
    carrier_id = fields.Many2one('tt.transport.carrier','Carrier',required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type',related="carrier_id.provider_type_id")
    is_default = fields.Boolean("Default Search", help="Usually on ALL")
    is_favorite = fields.Boolean("Favorite Search", help="Will make this search appear on top of the list")
    sequence = fields.Integer("Sequence",default=200)

    def get_provider_type_domain(self):
        return [('provider_type_id','=',self.provider_type_id.id)]

    provider_ids = fields.Many2many('tt.provider','tt_transport_provider_rel','search_carrier_id','provider_id','Provider',
                                    domain=get_provider_type_domain)
    active = fields.Boolean('Active', default=True)

    @api.onchange('carrier_id')
    def _onchange_search_display_name(self):
        if self.carrier_id:
            self.name = self.carrier_id.name

    @api.onchange('carrier_id')
    def _onchange_domain_agent_id(self):
        return {'domain': {
            'provider_ids': self.get_provider_type_domain()
        }}

    def to_dict(self):
        res = self.carrier_id and self.carrier_id.to_dict() or {}
        provider_ids = [rec.code for rec in self.provider_ids]
        res.update({
            'display_name': self.name,
            'provider': provider_ids,
            'is_favorite': self.is_favorite
        })
        return res

    def get_carrier_list_search_api(self, _is_all_data = False):
        try:
            search_param = []
            if not _is_all_data:
                search_param = [('active', '=', True)]
            _obj = self.sudo().with_context(active_test=False).search(search_param)
            res = {}
            for idx,rec in enumerate(_obj):
                curr_rec = rec.to_dict()
                if rec.is_default:
                    res[curr_rec['code']] = curr_rec
                else:
                    res["%s~%s" % (curr_rec['code'],idx+1)] = curr_rec
            _logger.info(json.dumps(res))
            res = ERR.get_no_error(res)
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(additional_message="Get Carrier List Error")
        return res

    def toggle_default(self):
        self.is_default = not self.is_default

    def toggle_favorite(self):
        self.is_favorite = not self.is_favorite