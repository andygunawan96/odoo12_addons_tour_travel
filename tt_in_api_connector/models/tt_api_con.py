from odoo import api,fields,models
import odoo.tools as tools
from ...tools import ERR,util
from ...tools.ERR import RequestException
import logging,traceback,json

_logger = logging.getLogger(__name__)

class TtApiCon(models.Model):
    _name = 'tt.api.con'
    _description = 'Base API Con'

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
    def _send_request(self,url,data,header,content_type='json',request_type='', timeout=30):
        try:
            res = util.send_request(url,data,header,content_type=content_type,request_type=request_type, timeout=timeout)
            if res['error_code'] != 0:
                raise RequestException(997,additional_message=res['error_msg'])
            res = res['response']['result']
            if res['error_code'] != 0:
                raise RequestException(998,additional_message=res['error_msg'])
            return res
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
        return res

    def _gateway_sign_in(self,co_uid = ''):
        sign_in_req = {
            'user': self.username,
            'password': self.password,
            'api_key': self.api_key,
        }
        if co_uid:
            sign_in_req['co_uid'] = co_uid
        res = self._send_request(
            '%s/session' % (self.url),
            sign_in_req,
            self._get_header('signin'),
            content_type='json'
        )
        if res['error_code'] != 0:
            raise Exception(res['error_msg'])
        return res['response']['signature']

    def _get_header(self, service_name, signature = ''):
        return {
            "Accept": "application/json,text/html,application/xml",
            "Content-Type": "application/json",
            "action": service_name,
            "signature": signature,
        }

    def send_request_to_gateway(self,url,data,service_name,content_type='json',request_type='', timeout=30):
        try:
            authorization = tools.config.get('backend_authorization', '')
            credential = util.decode_authorization(authorization)
            self.uid = credential.get('uid', -1)
            self.username = credential.get('username','')
            self.password = credential.get('password','')
            self.api_key = self.env['tt.api.credential'].search([('user_id','=',self.uid),('api_role','=','admin')],limit=1).api_key
        except Exception as e:
            _logger.error('Backend Connector Config Error, %s' % str(e))
        signature = self._gateway_sign_in(data.get('proxy_co_uid',''))
        res = self._send_request(url,data,self._get_header(service_name, signature),content_type=content_type,request_type=request_type,timeout=timeout)
        res['signature'] = signature
        return res
