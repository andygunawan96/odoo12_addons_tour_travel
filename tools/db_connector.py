import odoo.tools as tools
from xmlrpc import client as xmlrpclib
from . import util
from .api import Response
import logging


_logger = logging.getLogger(__name__)

class DbConnector(object):
    def __init__(self):
        self.url = ''
        self.db_name = ''
        self.uid = ''
        self.password = ''

    def _validate(self):
        if not self.url:
            raise Exception('Url is not defined in config')
        if not self.db_name:
            raise Exception('Database name is not defined in config')
        # if not self.uid or not self.password:
        #     raise Exception('Failed to get User Credential')

    def models(self):
        return xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(self.url), allow_none=True)

    def common(self):
        return xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(self.url))

    def execute(self, _model_name, _function_name, _parameters):
        try:
            res = self.models().execute_kw(self.db_name, self.uid, self.password, _model_name, _function_name, _parameters)
        except Exception as e:
            res = Response().get_error('Error db connector execution, %s' % str(e), 500)
        return res

    def authenticate(self, username, password, otp_params=False):
        try:
            res = self.common().authenticate(self.db_name, username, password, {}, otp_params)
            if not res:
                return False
            return res
        except Exception as e:
            _logger.error('Authentication Error, %s' % str(e))
            return False


class BackendConnector(DbConnector):
    def __init__(self):
        DbConnector.__init__(self)
        self._config()

    def _config(self):
        try:
            authorization = tools.config.get('backend_authorization', '')
            credential = util.decode_authorization(authorization)
            self.url = tools.config.get('backend_url', '')
            self.db_name = tools.config.get('backend_db', '')
            self.uid = credential.get('uid', 0)
            self.password = credential.get('password', '')
            self._validate()
        except Exception as e:
            _logger.error('Backend Connector Config Error, %s' % str(e))

    def get_error_code_api(self):
        res = self.execute('tt.error.api', 'get_error_code_api', [False])
        return res


class GatewayConnector(DbConnector):
    def __init__(self):
        DbConnector.__init__(self)
        self._config()

    def _config(self):
        try:
            authorization = tools.config.get('gateway_authorization', '')
            credential = util.decode_authorization(authorization)
            self.url = tools.config.get('gateway_url', '')
            self.db_name = tools.config.get('gateway_db', '')
            self.uid = credential.get('uid', 0)
            self.password = credential.get('password', '')
            self._validate()
        except Exception as e:
            _logger.error('Gateway Connector Error, %s' % str(e))

    def get_error_code_api(self):
        res = self.execute('tt.error.api', 'get_error_code_api', [False])
        return res

    def send_telegram_message(self, data, context):
        res = self.execute('tt.telegram.account', 'action_send_message_api', [False, data, context])
        return res

    def telegram_notif_api(self, data, context):
        res = self.execute('tt.error.api', 'telegram_notif_api', [False, data, context])
        return res

    # def g1 res = self.execute('tt.error.api', 'telegram_notif_api', [False, data, context])