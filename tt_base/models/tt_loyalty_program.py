from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime, timedelta
from ...tools import ERR
import json, logging
import traceback


_logger = logging.getLogger(__name__)


class TtLoyaltyProgram(models.Model):
    _name = 'tt.loyalty.program'
    _inherit = 'tt.history'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', default='')
    description = fields.Text('Description', default='')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        res = {
            'name': self.name,
            'code': self.code,
            'description': self.description and self.description or '',
        }
        return res

    def get_loyalty_program_list_api(self):
        try:
            _objs = self.env['tt.loyalty.program'].sudo().search([('active', '=', 1)])
            loyalty_program_list = [rec.to_dict() for rec in _objs]
            result = {
                'loyalty_program_list': loyalty_program_list,
            }
            res = ERR.get_no_error(result)
        except Exception as e:
            _logger.error('Error Get Loyalty Program List API, %s' % traceback.format_exc())
            res = ERR.get_error(500)
        return res

    def get_id(self, _code):
        try:
            _obj = self.env['tt.loyalty.program'].search([('code', '=', _code)], limit=1)
            if not _obj:
                return False
            return _obj.id
        except:
            _logger.error('Error Get Loyalty Program ID, %s' % traceback.format_exc())
            return False
