from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
import odoo.tools as tools

_logger = logging.getLogger(__name__)

class UserDuplicatePermissions(models.TransientModel):
    _name = "res.users.duplicate.permissions.wizard"
    _description = 'Res Users Duplicate Permissions Wizard'

    base_user_id = fields.Many2one('res.users', 'Base User',required=True)
    to_user_ids = fields.Many2many('res.users', 'res_users_duplicate_permissions_wizard_res_users_rel', 'from_user_id', 'to_user_id')

    def duplicate_permissions(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 68')
        try:
            group_id_list = []
            frontend_id_list = []
            for rec in self.base_user_id.groups_id:
                group_id_list.append(rec.id)
            for rec in self.base_user_id.frontend_security_ids:
                frontend_id_list.append(rec.id)
            for rec in self.to_user_ids:
                if not rec.is_user_template:
                    _logger.info('Updating Permissions: %s' % (rec.name))
                    rec.write({
                        'groups_id': [(6, 0, group_id_list)],
                        'frontend_security_ids': [(6, 0, frontend_id_list)]
                    })
        except Exception as e:
            _logger.info('Error Duplicate Permission')
            _logger.error(traceback.format_exc())
