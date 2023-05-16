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
            if res['error_code'] != 0 and res['error_code'] != 4006: ##4006 price change biar ke detect klo issued pakai bca
                raise RequestException(998,additional_message=res['error_msg'])
            return res
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500,additional_message=str(e))

    def _gateway_sign_in(self,co_uid=''):
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

    def send_request_to_gateway(self,url,data,service_name,content_type='json',request_type='', timeout=30, ho_id=''):
        try:
            authorization = tools.config.get('backend_authorization', '')
            credential = util.decode_authorization(authorization)
            self.uid = credential.get('uid', -1)
            self.username = credential.get('username','')
            self.password = credential.get('password','')
            if not ho_id:
                ho_id = self.env.user.agent_id.get_ho_parent_agent().id
            self.api_key = self.env['tt.api.credential'].search([('ho_id','=',ho_id),('api_role','=','admin')],limit=1).api_key
        except Exception as e:
            _logger.error('Backend Connector Config Error, ###%s###' % traceback.format_exc())
        signature = self._gateway_sign_in(data.get('proxy_co_uid',''))
        res = self._send_request(url,data,self._get_header(service_name, signature),content_type=content_type,request_type=request_type,timeout=timeout)
        res['signature'] = signature
        return res

    def send_cron_error_notification(self,cron_name):
        request = {
            'code': 9903,
            'message': '{}'.format(cron_name),
            "title": 'CRON ERROR'
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code')

    def send_ban_user_error_notification(self, user_name, reason, ho_id):
        request = {
            'code': 9901,
            'message': 'Ban user {} {}'.format(user_name, reason),
            "title": 'User ban <b>%s</b>' % (user_name)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url), request, 'notification_code', ho_id=ho_id)

    def send_new_ssr_notification(self, code, title, message, **kwargs):
        request = {
            'code': code,
            'title': title,
            'message': message
        }
        return self.send_request_to_gateway('%s/notification' % self.url, request, 'notification_code')

    def send_webhook_to_children(self, request):
        return self.send_request_to_gateway('%s/content' % self.url, request, 'send_webhook_to_children', timeout=request.get('timeout', 300))

    def send_reconcile_request(self,request, ho_id):
        return self.send_request_to_gateway('%s/account/%s' % (self.url,request['provider_type']),
                                            request['data'],
                                            'reconcile',
                                            timeout=120, ho_id=ho_id)
    def send_sync_status_visa(self, request):
        return self.send_request_to_gateway('%s/content' % self.url, request, 'sync_status_visa', timeout=300)

