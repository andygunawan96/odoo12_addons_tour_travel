from odoo import models, fields, api
from ...tools import variables
from ...tools.api import Response
import logging, traceback


_logger = logging.getLogger(__name__)


class ProviderType(models.Model):
    _name = 'tt.provider.type'
    _description = 'Rodex Model'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)

    def fill_provider_type(self):
        provider_type_obj = self.search([])
        variables.PROVIDER_TYPE = []
        variables.ADJUSTMENT_TYPE = []
        for rec in provider_type_obj:
            variables.PROVIDER_TYPE.append(rec.code)
            variables.ADJUSTMENT_TYPE.append((rec.code,rec.code.capitalize()))

    def _register_hook(self):
        self.fill_provider_type()
        print(variables.PROVIDER_TYPE)
        print(variables.ADJUSTMENT_TYPE)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
        }
        return res

    def get_provider_type_list_api(self, data, context):
        try:
            _objs = self.sudo().search([])
            response = [rec.to_dict() for rec in _objs]
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Provider Type List, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res
