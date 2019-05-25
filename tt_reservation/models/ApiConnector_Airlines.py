from ...tools import util, ERR
import odoo.tools as tools
import json
from odoo.http import request

class ApiConnector_Airlines():

    token_permanent = ''
    user_cookie = ''
    def __init__(self, environment='prod'):
        self.credetial = {
            "user": tools.config.get('api_user'),
            "password": tools.config.get('api_password'),
            "api_key": tools.config.get('api_key'),
            "co_id": False,
            "url_api": tools.config.get('url_api'),
        }
        self.cookie = False
        self.environment = environment


    def signin(self, api_context):
        req_post = self.credetial.copy()
        # ## Error unbound method #
        # req_post['co_uid'] = request.session.uid
        # if api_context:
        req_post['co_uid'] = api_context['co_uid']
        res = self.send_request('signin', req_post)
        try:
            if res['http_code'] == 0:
                cookie = res['cookie']
                res = json.loads(res['response'])['result']
                res['cookie'] = cookie
            else:
                res['error_code'] = res['http_code']
        except Exception:
            err = 3010
            res = {
                'error_code': err,
                'error_msg': ERR.GetError(err),
                'response': ''
            }
        return res

    def get_booking2(self, pnr, provider, direcion='OW', sid_order=None, api_context=None):
        signinRS = self.signin(api_context)   #MUST Always SIGNIN
        req_post = {
            'pnr': pnr,
            'provider': provider,
            'direction': direcion,  #use for compute r.ac per pax/rute(OW/RT)
            'sid_order': sid_order
        }
        res = self.send_request('get_booking2', req_post, cookie=signinRS['cookie'], timeout=60*5)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))

        res = json.loads(res['response'])
        # res = res['result']
        # if res['error_code'] != 0:
        #     raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        return res

    def ISSUED2(self, pnr, notes, provider_id, order_number, provider, api_context=None):
        signinRS = self.signin(api_context)
        # Fixme: Auto sign if session expire
        req_post = {
            'order_number': order_number,
            'pnr': pnr,
            'notes': notes,
            'provider': provider,
            'provider_id': provider_id,
        }
        res = self.send_request('issued2', req_post, cookie=signinRS['cookie'], timeout=60*5)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        res['response'] = json.loads(res['response'])
        if res['response']['result']['error_code'] != 0:
            # 'Fixed: Auto sign if session expire'
            self.cookie = None

        return res['response']

    def ISSUED_RECONCILE(self, date_from, date_to, provider, type, report_type, api_context=None):
        signinRS = self.signin(api_context)
        req_post = {
            'date_from': date_from,
            'provider': provider,
            'date_to': date_to,
            'type': type,
            'report_type': report_type,
        }
        res = self.send_request('issued_reconcile', req_post, cookie=signinRS['cookie'], timeout=300)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        return res

    def GET_AGENT_LEDGER(self, limit, offset, api_context=None):
        signinRS = self.signin(api_context)
        req_post = {
            'limit': limit,
            'offset': offset,
        }
        res = self.send_request('get_agent_ledger', req_post, cookie=signinRS['cookie'], timeout=300)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        return res

    def GET_TOP_UP(self, limit, offset, api_context=None):
        signinRS = self.signin(api_context)
        req_post = {
            'limit': limit,
            'offset': offset,
        }
        res = self.send_request('get_top_up', req_post, cookie=signinRS['cookie'], timeout=300)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        return res

    def SYNC_HOLD_DATE(self, req_data, api_context=None):
        signinRS = self.signin(api_context)
        req_post = req_data
        res = self.send_request('sync_hold_date', req_post, cookie=signinRS['cookie'], timeout=300)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        try:
            res = json.loads(res['response'])['result']
            # if res['error_code'] != 0:
            #     raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        except Exception as e:
            raise Exception(str(e))
        return res

    def SYNC_REPRICING(self, req_data, api_context=None):
        signinRS = self.signin(api_context)
        req_post = req_data
        res = self.send_request('sync_repricing', req_post, cookie=signinRS['cookie'], timeout=300)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        try:
            res = json.loads(res['response'])['result']
            # if res['error_code'] != 0:
            #     raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        except Exception as e:
            raise Exception(str(e))
        return res

    def send_request(self, action, post=None, cookie=None, timeout=None):
        url = '{}/airlines/booking'.format(self.credetial['url_api'])
        if action in ['signin']:
            url = '{}/airlines/session'.format(self.credetial['url_api'])

        headers = {
            "Accept": "application/json,text/html,application/xml",
            "Content-Type": "application/json",
            'cookie': cookie,
            'action': action
        }
        return util.send_request_json(url, post=post, headers=headers, timeout=timeout)

    def get_booking_from_vendor(self, req_post, api_context=None):
        signinRS = self.signin(api_context)
        # Fixme: Auto sign if session expire
        res = self.send_request('get_booking_from_vendor', req_post, cookie=signinRS['cookie'], timeout=60*5)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        res = json.loads(res['response'])['result']
        if res['error_code'] != 0:
            raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        return res

    def balance_notification(self, req_data, api_context=None):
        signinRS = self.signin(api_context)
        req_post = req_data
        res = self.send_request('balance_notification', req_post, cookie=signinRS['cookie'], timeout=300)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        try:
            res = json.loads(res['response'])['result']
            # if res['error_code'] != 0:
            #     raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        except:
            raise Exception('%s %s' % (-1, 'Error to get the result'))
        return res

    def GetTicketNumber(self, pnr, notes, provider, api_context=None):
        signinRS = self.signin(api_context)
        req_post = {
            'pnr': pnr,
            'notes': notes,
            'provider': provider,
        }
        res = self.send_request('get_ticket_number', req_post, cookie=signinRS['cookie'], timeout=60*5)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        res['response'] = json.loads(res['response'])
        return res['response']['result']
