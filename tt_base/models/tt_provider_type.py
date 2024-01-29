from odoo import models, fields, api
from odoo.exceptions import UserError
from ...tools import variables
from ...tools.api import Response
import logging, traceback


_logger = logging.getLogger(__name__)


class ProviderType(models.Model):
    _name = 'tt.provider.type'
    _description = 'Provider Type'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 421')
        return super(ProviderType, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 422')
        return super(ProviderType, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager') or not self.env.user.has_group('tt_base.group_provider_level_5'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 423')
        return super(ProviderType, self).unlink()

    def get_provider_type(self):
        provider_type_obj = self.search([('id', '!=', self.env.ref('tt_base.tt_provider_type_payment').id), ('id', '!=', self.env.ref('tt_base.tt_provider_type_bank').id)])
        provider_type = []
        for rec in provider_type_obj:
            provider_type.append(rec.code)
        return provider_type

    def _register_hook(self):
        variables.PROVIDER_TYPE = self.get_provider_type()

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
            'active': self.active,
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
