from odoo import api, fields, models, _
from ...tools.api import Response
import logging
import traceback
from ...tools.db_connector import GatewayConnector


_logger = logging.getLogger(__name__)
_gw_con = GatewayConnector()


class TtSSRCategory(models.Model):
    _name = 'tt.ssr.category'
    _description = 'SSR Category'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    key = fields.Char('Key', required=True, help='Key pada response dari API ke User API', default='')
    icon = fields.Char('Icon')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
            'key': self.key,
            'active': self.active,
        }
        return res

    def get_data(self):
        res = {
            'name': self.name,
            'code': self.code,
            'key': self.key,
        }
        return res


class TtSSRList(models.Model):
    _name = 'tt.ssr.list'
    _description = 'SSR List'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description', default='')
    rules = fields.Text('Rules', default='')
    notes = fields.Text('Notes', default='')
    category_id = fields.Many2one('tt.ssr.category', 'Category')
    provider_id = fields.Many2one('tt.provider', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', required=True)
    image_url = fields.Char('Image Url', default='')
    line_ids = fields.One2many('tt.ssr.list.line', 'ssr_id', 'Lines')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        line_ids = [rec.to_dict() for rec in self.line_ids]
        res = {
            'name': self.name,
            'code': self.code,
            'description': self.description and self.description or '',
            'rules': self.rules and self.rules or '',
            'notes': self.notes and self.notes or '',
            'category_id': self.category_id and self.category_id.to_dict() or {},
            'provider_id': self.provider_id and self.provider_id.to_dict() or {},
            'provider_type_id': self.provider_type_id and self.provider_type_id.to_dict() or {},
            'line_ids': line_ids,
            'image_url': self.image_url and self.image_url or '',
        }
        return res

    def create_ssr_api(self, req_data, provider, provider_type):
        try:
            provider_type_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
            if not provider_type_obj:
                raise Exception('Provider Type not found, %s' % provider_type)
            if not provider_obj:
                raise Exception('Provider not found, %s' % provider)

            _obj = self.sudo().search([('code', '=', req_data['code']), ('provider_id', '=', provider_obj.id), ('provider_type_id', '=', provider_type_obj.id)])
            if _obj:
                # raise Exception('Data is Similar, %s' % req_data['code'])
                _logger.info('Data is similar, %s' % req_data)
                response = _obj.get_ssr_data()
                return Response().get_no_error(response)

            req_data.update({
                'provider_id': provider_obj.id,
                'provider_type_id': provider_type_obj.id
            })

            _obj = self.sudo().create(req_data)
            values = {
                'code': 9901,
                'title': 'New SSR Created',
                'message': 'Please complete ssr detail for %s in %s (%s)' % (_obj.code, _obj.provider_id.code, _obj.provider_type_id.code)
            }
            self.env['tt.api.con'].sudo().send_new_ssr_notification(**values)
            # _gw_con.telegram_notif_api(values, {})
            response = _obj.get_ssr_data()
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Create SSR API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_ssr_data(self):
        lines = [rec.to_dict() for rec in self.line_ids]
        res = {
            'name': self.name,
            'code': self.code,
            'description': self.description and self.description or '',
            'rules': self.rules and self.rules or '',
            'notes': self.notes and self.notes or '',
            'category_id': self.category_id and self.category_id.get_data() or '',
            'provider_id': self.provider_id and self.provider_id.get_data() or '',
            'lines': lines,
            'image_url': self.image_url and self.image_url or '',
        }
        return res

    def get_ssr_api(self, provider_type):
        try:
            provider_type_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            # provider_obj = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
            if not provider_type_obj:
                raise Exception('Provider Type not found, %s' % provider_type)
            # if not provider_obj:
            #     raise Exception('Provider not found, %s' % provider)

            # _objs = self.sudo().search([('provider_id', '=', provider_obj.id), ('provider_type_id', '=', provider_type_obj.id), ('active', '=', 1)])
            _objs = self.sudo().search([('provider_type_id', '=', provider_type_obj.id), ('active', '=', 1)])
            # response = [rec.get_ssr_data() for rec in _objs]
            ssrs = [rec.get_ssr_data() for rec in _objs]
            response = {
                'ssrs': ssrs,
                'provider_type': provider_type,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get SSR API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_ssr_api_by_code(self, provider, provider_type):
        try:
            provider_type_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
            if not provider_type_obj:
                raise Exception('Provider Type not found, %s' % provider_type)
            if not provider_obj:
                raise Exception('Provider not found, %s' % provider)

            _objs = self.sudo().search([('provider_id', '=', provider_obj.id), ('provider_type_id', '=', provider_type_obj.id), ('active', '=', 1)])
            response = {}
            [response.update({rec.code: rec.get_ssr_data()}) for rec in _objs]
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get SSR API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    # November 11, 2021 - SAM
    # New Get SSR API
    def get_ssr_data_api(self):
        try:
            objs = self.env['tt.ssr.list'].sudo().search([])
            ssr_data = {}
            for obj in objs:
                if not obj.active:
                    continue

                provider_type_code = obj.provider_type_id.code if obj.provider_type_id else ''
                provider_code = obj.provider_id.code if obj.provider_id else ''

                if not provider_type_code or not provider_code:
                    continue

                vals = obj.get_ssr_data()
                ssr_code = vals['code']
                if not ssr_code:
                    continue

                if provider_type_code not in ssr_data:
                    ssr_data[provider_type_code] = {
                        'provider_dict': {},
                    }

                if provider_code not in ssr_data[provider_type_code]['provider_dict']:
                    ssr_data[provider_type_code]['provider_dict'][provider_code] = {
                        'ssr_dict': {}
                    }

                ssr_data[provider_type_code]['provider_dict'][provider_code]['ssr_dict'][ssr_code] = vals

            payload = {
                'ssr_data': ssr_data
            }
        except Exception as e:
            _logger.error('Error Get SSR Data, %s' % traceback.format_exc())
            payload = {}
        return payload


class TtSSRListLine(models.Model):
    _name = 'tt.ssr.list.line'
    _description = 'SSR List Line'

    name = fields.Char('Name', required=True)
    sequence = fields.Integer(default=50, readonly=1)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description', default='')
    rules = fields.Text('Rules', default='')
    notes = fields.Text('Notes', default='')
    value = fields.Char('Value', default='')
    ssr_id = fields.Many2one('tt.ssr.list', 'SSR', readonly=1)
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
            'value': self.value,
            'description': self.description,
            'rules': self.rules,
            'notes': self.notes,
        }
        return res


class TtProviderSSRListInherit(models.Model):
    _inherit = 'tt.provider'

    ssr_ids = fields.One2many('tt.ssr.list', 'provider_id', 'SSRs')

    def to_dict(self):
        ssr_ids = [rec.to_dict() for rec in self.ssr_ids]
        res = super(TtProviderSSRListInherit, self).to_dict()
        res.update({
            'ssr_ids': ssr_ids
        })
        return res
