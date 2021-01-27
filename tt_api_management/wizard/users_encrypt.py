from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import util
from ...tools.db_connector import BackendConnector


class UserEncryptInherit(models.Model):
    _inherit = 'res.users'

    def action_show_encrypt(self):
        values = {
            'uid': self.id,
            'username': self.login,
            'password': '',
        }
        _obj = self.env['tt.user.encrypt'].create(values)
        wizard_form = self.env.ref('tt_api_management.user_encrypt_form_view', False)
        return {
            'name': _('User Encrypt'),
            'type': 'ir.actions.act_window',
            'res_model': 'tt.user.encrypt',
            'res_id': _obj.id,
            'view_id': wizard_form.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }


class UserEncryptWizard(models.TransientModel):
    _name = 'tt.user.encrypt'
    _description = 'User Encrypt'

    uid = fields.Integer(string='User ID', readonly=1)
    username = fields.Char(string='Username', readonly=1)
    password = fields.Char(string='Password')
    result = fields.Char(string='Result', readonly=1)

    def compute_authorization(self):
        _db_con = BackendConnector()
        _db_con._validate()
        is_authenticate = _db_con.authenticate(self.username, self.password)
        if not is_authenticate:
            raise UserError(_('Username and Password are not match'))
        self.result = util.encode_authorization(self.uid, self.username, self.password)
        wizard_form = self.env.ref('tt_api_management.user_encrypt_form_view', False)
        return {
            'name': _('User Encrypt'),
            'type': 'ir.actions.act_window',
            'res_model': 'tt.user.encrypt',
            'res_id': self.id,
            'view_id': wizard_form.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }
