from odoo import api,fields,models
import odoo.tools as tools
from ...tools import ERR,util
from ...tools.ERR import RequestException
import logging,traceback,json

_logger = logging.getLogger(__name__)

class TtApiCon(models.Model):
    _name = 'tt.api.con'

    table_name = ''
    url = tools.config.get('gateway_url', '')

    def api_webservice(self,action,data,context):
        try:
            try:
                table_obj = self.env[self.table_name]
            except:
                raise RequestException(1000)

            res = self.action_call(table_obj,action,data,context)

        except RequestException as e:
            _logger.error(traceback.format_exc())
            res = e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error()
        return res

    def action_call(self,table_obj,action,data,context):
        pass

    #call to gateway as webservice not as xmlrpc
    def _send_request(self,url,data,service_name,is_json=True, timeout=30):
        try:
            authorization = tools.config.get('backend_authorization', '')
            credential = util.decode_authorization(authorization)
            self.uid = credential.get('uid', -1)
            self.username = credential.get('username','')
            self.password = credential.get('password', '')
            self.api_key = self.env['tt.api.credential'].search([('user_id','=',self.uid),('api_role','=','admin')],limit=1).api_key
        except Exception as e:
            _logger.error('Backend Connector Config Error, %s' % str(e))
        try:
            signature = self._gateway_sign_in()
            res = util.send_request(url,data,self._get_header(service_name,signature),is_json=is_json, timeout=timeout)
            return res
        except Exception as e:
            _logger.error(traceback.format_exc())
        return ERR.get_error()

    def _gateway_sign_in(self):
        res = util.send_request(
            '%s/session' % (self.url)
            ,{
                'user': self.username,
                'password': self.password,
                'api_key': self.api_key,
            },
            self._get_header('signin'),
            is_json=True
        )

        if res['error_code'] != 0:
            raise ERR.get_error()

        return res['response']['signature']

    def _get_header(self, service_name, signature = ''):
        return {
            "Accept": "application/json,text/html,application/xml",
            "Content-Type": "application/json",
            "action": service_name,
            "signature": signature,
        }
