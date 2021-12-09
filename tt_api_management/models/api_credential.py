from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables
from ...tools.ERR import RequestException
from ...tools.db_connector import BackendConnector
from ...tools.api import Response
from datetime import datetime,timedelta
import uuid, base64
import logging, traceback

_DB_CON = BackendConnector()
_logger = logging.getLogger(__name__)


class ApiManagement(models.Model):
    _name = 'tt.api.credential'
    _description = 'API Credential'

    name = fields.Char('Name', required=True)
    api_key = fields.Char(string='API Key')
    active = fields.Boolean(string='Active', default=True)
    api_role = fields.Selection(selection=variables.ROLE_TYPE, required=True, default='operator')
    device_type = fields.Selection(selection=variables.DEVICE_TYPE, default='general')
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
            'device_type': self.device_type,
        }
        return res

    def get_credential(self):
        res = {} if not self.user_id else self.user_id.get_credential()
        res.update({
            'api_role': self.api_role,
            'device_type': self.device_type,
        })
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

            if _user.is_banned:
                additional_msg = ""
                try:
                    additional_msg = 'Until %s.' % datetime.strftime(self.env['tt.ban.user'].search([('user_id', '=', _user.id)], limit=1).end_datetime+timedelta(hours=7), '%Y-%m-%d %I %p')
                except:
                    pass
                raise RequestException(1029,additional_message=additional_msg)
            if not _user.is_api_user:
                raise Exception('User is not allowed to access API')

            _obj = self.sudo().search([('user_id', '=', uid), ('api_key', '=', data['api_key']),
                                       ('active', '=', 1)], limit=1)
            if not _obj:
                raise Exception('API Key is not match')

            values = _user.get_credential(prefix='co_')
            values.update({
                'sid': context['sid'],
                'signature': self._generate_signature(),
            })
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

                if _co_user.is_banned:
                    additional_msg = ""
                    try:
                        addtional_msg = 'Until %s.' % datetime.strftime(
                            self.env['tt.ban.user'].search([('user_id', '=', _co_user.id)],
                                                           limit=1).end_datetime+timedelta(hours=7),
                            '%Y-%m-%d %I %p')
                    except:
                        pass
                    raise RequestException(1029, additional_message=addtional_msg)

                values.update(_co_user.get_credential(prefix='co_'))
            if data.get('co_uid'):
                if response['api_role'] != 'admin':
                    raise Exception('User Role is not allowed.')
                _co_user = self.env['res.users'].sudo().browse(int(data['co_uid']))
                values.update(_co_user.get_credential(prefix='co_'))
            response.update(values)

            # April 9, 2019 - SAM
            # Menambahkan uplines dari user
            co_user_info = self.env['tt.agent'].sudo().get_agent_level(response['co_agent_id'])
            response['co_user_info'] = co_user_info
            res = Response().get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def get_userid_credential(self, data):
        try:
            _user = self.env['res.users'].sudo().browse(int(data['user_id']))

            if _user.is_banned:
                additional_msg = ""
                try:
                    additional_msg = 'Until %s.' % datetime.strftime(self.env['tt.ban.user'].search([('user_id', '=', _user.id)], limit=1).end_datetime+timedelta(hours=7), '%Y-%m-%d %I %p')
                except:
                    pass
                raise RequestException(1029,additional_message=additional_msg)
            if not _user.is_api_user:
                raise Exception('User is not allowed to access API')

            _obj = self.sudo().search([('user_id', '=', int(data['user_id'])), ('api_key', '=', data['api_key']),
                                       ('active', '=', 1)], limit=1)
            if not _obj:
                raise Exception('API Key is not match')

            values = _user.get_credential(prefix='co_')
            values.update({
                'signature': self._generate_signature()
            })
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

                if _co_user.is_banned:
                    additional_msg = ""
                    try:
                        addtional_msg = 'Until %s.' % datetime.strftime(
                            self.env['tt.ban.user'].search([('user_id', '=', _co_user.id)],
                                                           limit=1).end_datetime+timedelta(hours=7),
                            '%Y-%m-%d %I %p')
                    except:
                        pass
                    raise RequestException(1029, additional_message=addtional_msg)

                values.update(_co_user.get_credential(prefix='co_'))
            if data.get('co_uid'):
                if response['api_role'] != 'admin':
                    raise Exception('User Role is not allowed.')
                _co_user = self.env['res.users'].sudo().browse(int(data['co_uid']))
                values.update(_co_user.get_credential(prefix='co_'))
            response.update(values)

            # April 9, 2019 - SAM
            # Menambahkan uplines dari user
            co_user_info = self.env['tt.agent'].sudo().get_agent_level(response['co_agent_id'])
            response['co_user_info'] = co_user_info
            res = Response().get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res


class ResUsersApiInherit(models.Model):
    _inherit = 'res.users'

    is_api_user = fields.Boolean(string='API User', default=False)
    credential_ids = fields.One2many(comodel_name='tt.api.credential', inverse_name='user_id', string='Credentials')

    def get_credential(self, prefix=''):

        res = {
            '%suid' % prefix: self.id,
            '%suser_name' % prefix: self.name,
            '%suser_login' % prefix: self.login,
            '%sagent_id' % prefix: '',
            '%sagent_name' % prefix: '',
            '%sagent_type_id' % prefix: '',
            '%sagent_type_name' % prefix: '',
            '%sagent_type_code' % prefix: '',
            '%sagent_frontend_security' % prefix: [rec.code for rec in self.frontend_security_ids]
        }
        if self.agent_id:
            res.update(self.agent_id.get_credential(prefix))
        if self.customer_parent_id:
            res.update(self.customer_parent_id.get_credential(prefix))
        if self.customer_id:
            res.update(self.customer_id.get_credential(prefix))
        return res

    def reset_password_api(self, data, context):
        try:
            # September 2, 2019 - SAM
            # Ganti mekanisme dengan mengirimkan email
            # user_obj = self.sudo().browse(int(context['co_uid']))
            user_obj = self.sudo().search([('login', '=', data['email'])], limit=1)
            if not user_obj:
                raise Exception('User does not exist')
            user_obj.action_reset_password()
            res = Response().get_no_error()
        except Exception as e:
            _logger.error('Error Reset Password API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

class TtAgentApiInherit(models.Model):
    _inherit = 'tt.agent'

    def get_credential(self, prefix=''):
        res = {
            '%sagent_id' % prefix: self.id,
            '%sagent_name' % prefix: self.name,
        }
        if self.agent_type_id:
            res.update(self.agent_type_id.get_credential(prefix))
        return res

    def ban_user_api(self, duration=1576800):  # default = 3 tahun
        for rec in self.user_ids:
            if rec.is_api_user:
                self.env['tt.ban.user'].ban_user(rec.id, duration)
                try:
                    self.env['tt.api.con'].send_ban_user_error_notification(rec.name, 'error payment quota')
                except Exception as e:
                    _logger.error('Ban User Error %s %s' % (str(e), traceback.format_exc()))

    def unban_user_api(self):
        for rec in self.user_ids:
            if rec.is_api_user:
                self.env['tt.ban.user'].unban_user(rec.id)

class TtAgentTypeApiInherit(models.Model):
    _inherit = 'tt.agent.type'

    def get_credential(self, prefix=''):
        res = {
            '%sagent_type_id' % prefix: self.id,
            '%sagent_type_name' % prefix: self.name,
            '%sagent_type_code' % prefix: self.code,
            # '%sagent_type_quota' % prefix: self.is_using_pnr_quota
        }
        return res

class TtCustomerParentApiInherit(models.Model):
    _inherit = 'tt.customer.parent'

    def get_credential(self, prefix=''):
        res = {
            '%scustomer_parent_id' % prefix: self.id,
            '%scustomer_parent_name' % prefix: self.name,
        }
        if self.customer_parent_type_id:
            res.update(self.customer_parent_type_id.get_credential(prefix))
        return res

class TtCustomerParentTypeApiInherit(models.Model):
    _inherit = 'tt.customer.parent.type'

    def get_credential(self, prefix=''):
        res = {
            '%scustomer_parent_type_id' % prefix: self.id,
            '%scustomer_parent_type_name' % prefix: self.name,
            '%scustomer_parent_type_code' % prefix: self.code,
        }
        return res

class TtCustomerApiInherit(models.Model):
    _inherit = 'tt.customer'

    def get_credential(self, prefix=''):
        res = {
            '%scustomer_seq_id' % prefix: self.seq_id,
        }
        return res