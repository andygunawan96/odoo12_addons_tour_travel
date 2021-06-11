from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
import odoo.tools as tools

_logger = logging.getLogger(__name__)

class FrontendSecurityAssign(models.TransientModel):
    _name = "frontend.security.assign.wizard"
    _description = 'Frontend Security Assign Wizard'

    frontend_security_id = fields.Many2one('tt.frontend.security', 'Frontend Security',required=True)
    to_user_ids = fields.Many2many('res.users', 'frontend_security_assign_wizard_res_users_rel', 'frontend_security_id', 'to_user_id')

    def assign_security(self):
        for rec in self.to_user_ids:
            rec.write({
                'frontend_security_ids': [(4, self.frontend_security_id.id)]
            })
