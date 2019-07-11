from odoo import api, fields, models, _
import re
import logging
import traceback
from ...tools.api import Response


_logger = logging.getLogger(__name__)


class TransportCarrier(models.Model):
    _name = 'tt.transport.carrier'
    _description = "List of Carrier Code"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', help="for airline : 2-letter IATA")
    icao = fields.Char('ICAO Code', help="ICAO code for airline")
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    call_sign = fields.Char('Call Sign')
    # cancellation_policy = fields.Html('Cancellation Policy')
    # general_policy = fields.Html('General Policy')

    # logo = fields.Binary('Logo', attachment=True,
    #     help='This field holds the image used as avatar for this contact, limited to 1024x1024px')

    active = fields.Boolean('Active', default='True')
    # country_id = fields.Many2one('res.country', 'Country') masihbutuh?

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        pos = self.search(domain + args, limit=limit)
        return pos.name_get()

    def get_id(self, code, provider_type):
        res = self.sudo().search([('code', '=', code), ('provider_type_id', '=', provider_type.id)])
        return res and res[0].id or False

    def get_carrier_info(self, code):
        res = self.sudo().search([('code','=',code)], limit=1)
        if res:
            return {
                'name': res[0].name,
                'code': res[0].code,
                'display_name': res[0].display_name,
                'logo': res[0].logo,
            }
        return {
                'name': code,
                'code': code,
                'display_name': code,
                'logo': False,
            }

    def to_dict(self):
        return {
            'name': self.name,
            'code': self.code,
            'icao': self.icao,
            'provider_type_id': self.provider_type_id.to_dict(),
            'call_sign': self.transport_type,
            'active': self.active
        }

    def get_carrier_data(self):
        res = {
            'name': self.name,
            'code': self.code,
            'icao': self.icao,
            'call_sign': self.call_sign,
        }
        return res

    def get_carrier_list_by_code(self, _provider_type):
        provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
        if not provider_obj:
            raise Exception('Provider type not found, %s' % _provider_type)

        _obj = self.sudo().search([('provider_type_id', '=', provider_obj.id), ('active', '=', True)])
        res = {}
        for rec in _obj:
            code = rec.code
            res[code] = rec.get_carrier_data()
        return res

    def get_carrier_list_api(self, data, context):
        try:
            response = self.get_carrier_list_by_code(data['provider_type'])
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Carrier List, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res
