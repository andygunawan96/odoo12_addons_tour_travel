from odoo import api, fields, models
import logging
import traceback

_logger = logging.getLogger(__name__)

class TransportCarrier(models.Model):
    _name = 'tt.transport.carrier.search'
    _description = "List of Search Carrier Code"
    _rec_name = 'carrier_id'

    carrier_id = fields.Many2one('tt.transport.carrier','Carrier',required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type',related=carrier_id.provider_type_id)

    provider_ids = fields.Many2many('tt.provider','tt_transport_provider_rel','search_carrier_id','provider_id','Provider',
                                    domain=lambda self: self.get_provider_type_domain())
    active = fields.Boolean('Active', default=True)


    def get_provider_type_domain(self):
        return [('provider_type_id','=',self.provider_type_id)]

    def to_dict(self):
        res = self.carrier_id and self.carrier_id.to_dict() or {}
        provider_ids = [rec.code for rec in self.provider_ids]
        return res.update({
            'provider': provider_ids,
        })

    def get_carrier_list_search_api(self, _is_all_data = False):
        search_param = []
        if not _is_all_data:
            search_param = [('active', '=', True)]
        _obj = self.sudo().with_context(active_test=False).search(search_param)
        res = {}
        for rec in _obj:
            curr_rec = rec.to_dict()
            res[curr_rec.code] = curr_rec
        return res

