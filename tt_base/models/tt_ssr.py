from odoo import api, fields, models, _
from ...tools.api import Response
import logging
import traceback
from ...tools.db_connector import GatewayConnector


_logger = logging.getLogger(__name__)
_gw_con = GatewayConnector()


class TtSSRCategory(models.Model):
    _name = 'tt.ssr.category'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
            'active': self.active,
        }
        return res


class TtSSRList(models.Model):
    _name = 'tt.ssr.list'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description', default='')
    category_id = fields.Many2one('tt.ssr.category', 'Category')
    provider_id = fields.Many2one('tt.provider', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', required=True)
    line_ids = fields.One2many('tt.ssr.list.line', 'ssr_id', 'Lines')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        line_ids = [rec.to_dict() for rec in self.line_ids]
        res = {
            'name': self.name,
            'code': self.code,
            'description': self.description and self.description or '',
            'category_id': self.category_id and self.category_id.to_dict() or {},
            'provider_id': self.provider_id and self.provider_id.to_dict() or {},
            'provider_type_id': self.provider_type_id and self.provider_type_id.to_dict() or {},
            'line_ids': line_ids
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
            _gw_con.telegram_notif_api(values, {})
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
            'category_name': self.category_id and self.category_id.name or '',
            'category_code': self.category_id and self.category_id.code or '',
            'lines': lines,
        }
        return res

    def get_ssr_api(self, provider, provider_type):
        try:
            provider_type_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
            if not provider_type_obj:
                raise Exception('Provider Type not found, %s' % provider_type)
            if not provider_obj:
                raise Exception('Provider not found, %s' % provider)

            _objs = self.sudo().search([('provider_id', '=', provider_obj.id), ('provider_type_id', '=', provider_type_obj.id), ('active', '=', 1)])
            response = [rec.get_ssr_data() for rec in _objs]
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


class TtSSRListLine(models.Model):
    _name = 'tt.ssr.list.line'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    sequence = fields.Integer(default=50, readonly=1)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description', default='')
    value = fields.Char('Value', default='')
    ssr_id = fields.Many2one('tt.ssr.list', 'SSR', readonly=1)
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
            'value': self.value,
            'description': self.description,
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
