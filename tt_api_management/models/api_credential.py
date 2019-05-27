from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables
from ...tools.db_connector import BackendConnector
from ...tools.api import Response
from datetime import datetime
import uuid, base64


_DB_CON = BackendConnector()


class ApiManagement(models.Model):
    _name = 'tt.api.credential'

    api_key = fields.Char(string='API Key')
    active = fields.Boolean(string='Active', default=True)
    api_role = fields.Selection(selection=variables.ROLE_TYPE, required=True, default='operator')
    user_id = fields.Many2one(comodel_name='res.users', string='User')

    def to_dict(self):
        res = {
            'user_id': {
                'id': self.user_id.id,
                'name': self.user_id.name,
                'login': self.user_id.login,
            },
            'api_key': self.api_key and self.api_key or '',
            'api_role': self.api_role,
        }
        return res

    def get_credential(self):
        res = {
            'uid': self.user_id.id,
            'user_name': self.user_id.name,
            'user_login': self.user_id.login,
            'api_role': self.api_role,
        }
        return res

    @api.model
    def create(self, vals):
        if not vals['api_key']:
            vals['api_key'] = self._generate_api_key()
        res = super(ApiManagement, self).create(vals)
        return res

    def _generate_api_key(self):
        res = str(uuid.uuid4())
        return res

    def _generate_signature(self):
        res = str(uuid.uuid4()).replace('-', '')
        return res

    # def _generate_signature(self):
    #     timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    #     signature = '%s:%s' % (str(uuid.uuid4()), timestamp)
    #     res = base64.b64encode(signature.encode())
    #     return res

    def action_generate_api_key(self):
        if self.api_key:
            raise UserError(_('API Key has been generated, empty the field to generate the new one.'))
        self.api_key = self._generate_api_key()
        return True

    def get_credential_api(self, data, context):
        try:
            uid = _DB_CON.authenticate(data['user'], data['password'])
            if not uid:
                raise Exception('User and Password is not match')
            _user = self.env['res.users'].sudo().browse(uid)
            if not _user.is_api_user:
                raise Exception('User is not allowed to access API')

            _obj = self.sudo().search([('user_id', '=', uid), ('api_key', '=', data['api_key']),
                                       ('active', '=', 1)], limit=1)
            if not _obj:
                raise Exception('API Key is not match')

            values = {
                'co_uid': _user.id,
                'co_user_name': _user.name,
                'co_user_login': _user.login,
                'sid': context['sid'],
                'signature': self._generate_signature(),
            }
            response = _obj.get_credential()
            # April 11, 2019 - SAM
            # Sementara host IP dikosongkan hingga menemukan cara untuk mendapatkan host IP user
            # if not context['host_ip'] in response['host_ips']:
            #     raise Exception('Host IP is not allowed to access')
            if data.get('co_user') and data.get('co_password'):
                if response['api_role'] == 'operator':
                    raise Exception('User Role is not allowed to do Co User login')
                co_uid = _DB_CON.authenticate(data['co_user'], data['co_password'])
                if not co_uid:
                    raise Exception('Co User and Co Password is not match')
                _co_user = self.env['res.users'].sudo().browse(co_uid)
                values.update({
                    'co_uid': _co_user.id,
                    'co_user_name': _co_user.name,
                    'co_user_login': _co_user.login,
                })
            response.update(values)
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res


class ResUsersApiInherit(models.Model):
    _inherit = 'res.users'

    is_api_user = fields.Boolean(string='API User', default=False)
    credential_ids = fields.One2many(comodel_name='tt.api.credential', inverse_name='user_id', string='Credentials')
