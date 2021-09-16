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

    is_duplicate_single_name = fields.Boolean('Duplicate Single Name', default=True, help='Duplicate Single Name (first name and last name has same value)')
    adult_length_name = fields.Integer('Adult Length Name', default=30, help='Adult length name')
    child_length_name = fields.Integer('Child Length Name', default=30, help='Child length name')
    infant_length_name = fields.Integer('Infant Length Name', default=16, help='Infant length name')
    is_adult_birth_date_required = fields.Boolean('Is Adult Birth Date Required', default=True)
    required_identity_required_domestic = fields.Boolean('Is Identity Required Domestic', default=False)
    required_identity_required_international = fields.Boolean('Is Identity Required International', default=False)
    active = fields.Boolean('Active', default=True)
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
        res = self.sudo().search([('code', '=', code), ('provider_type_id', '=', provider_type.id)],limit=1)
        return res and res or False

    def to_dict(self):
        return {
            'name': self.name,
            'code': self.code,
            'icao': self.icao,
            # 'provider_type_id': self.provider_type_id.to_dict(),
            'call_sign': self.call_sign,
            'is_duplicate_single_name': self.is_duplicate_single_name,
            'adult_length_name': self.adult_length_name,
            'child_length_name': self.child_length_name,
            'infant_length_name': self.infant_length_name,
            'is_adult_birth_date_required': self.is_adult_birth_date_required,
            'required_identity_required_domestic': self.required_identity_required_domestic,
            'required_identity_required_international': self.required_identity_required_international,
            'active': self.active,
        }

    def get_carrier_data(self):
        res = {
            'name': self.name,
            'code': self.code and self.code or '',
            'icao': self.icao and self.icao or '',
            'call_sign': self.call_sign and self.call_sign or '',
            'provider_type': self.provider_type_id and self.provider_type_id.code or '',
            'is_duplicate_single_name': self.is_duplicate_single_name,
            'adult_length_name': self.adult_length_name,
            'child_length_name': self.child_length_name,
            'infant_length_name': self.infant_length_name,
            'is_adult_birth_date_required': self.is_adult_birth_date_required,
            'required_identity_required_domestic': self.required_identity_required_domestic,
            'required_identity_required_international': self.required_identity_required_international,
            'active': self.active,
        }
        return res

    def get_carrier_list_by_code(self, _provider_type, _is_all_data):
        provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
        if not provider_obj:
            raise Exception('Provider type not found, %s' % _provider_type)
        search_param = [('provider_type_id', '=', provider_obj.id)]
        if not _is_all_data:
            search_param = [('provider_type_id', '=', provider_obj.id), ('active', '=', True)]
        _obj = self.sudo().with_context(active_test=False).search(search_param)
        res = {}
        for rec in _obj:
            code = rec.code
            res[code] = rec.get_carrier_data()
        return res

    def get_carrier_list_api(self, data, context):
        try:
            response = self.get_carrier_list_by_code(data['provider_type'], data.get('is_all_data', False))
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Carrier List, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res


class TransportCarrierType(models.Model):
    _name = 'tt.transport.carrier.type'
    _description = "List of Carrier Type Code"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', help="for airline : IATA Code")
    icao = fields.Char('ICAO Code', help="ICAO code for airline")
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    active = fields.Boolean('Active', default=True)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        pos = self.search(domain + args, limit=limit)
        return pos.name_get()

    def get_id(self, code, provider_type):
        res = self.sudo().search([('code', '=', code), ('provider_type_id', '=', provider_type.id)],limit=1)
        return res and res or False

    def to_dict(self):
        return {
            'name': self.name,
            'code': self.code,
            'icao': self.icao,
            'active': self.active,
        }

    def get_carrier_type_data(self):
        res = {
            'name': self.name,
            'code': self.code and self.code or '',
            'icao': self.icao and self.icao or '',
            'provider_type': self.provider_type_id and self.provider_type_id.code or '',
            'active': self.active,
        }
        return res

    def get_carrier_type_list_by_code(self, _provider_type, _is_all_data):
        provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
        if not provider_obj:
            raise Exception('Provider type not found, %s' % _provider_type)
        search_param = [('provider_type_id', '=', provider_obj.id)]
        if not _is_all_data:
            search_param = [('provider_type_id', '=', provider_obj.id), ('active', '=', True)]
        _obj = self.sudo().with_context(active_test=False).search(search_param)
        res = {}
        for rec in _obj:
            code = rec.code
            res[code] = rec.get_carrier_type_data()
        return res

    def get_carrier_type_list_api(self, data, context):
        try:
            response = self.get_carrier_type_list_by_code(data['provider_type'], data.get('is_all_data', False))
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Carrier Type List, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res
