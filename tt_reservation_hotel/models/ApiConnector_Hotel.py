from ...tools import util, ERR
import odoo.tools as tools
import json
from odoo.http import request


class ApiConnectorHotels():

    token_permanent = ''
    user_cookie = ''

    def __init__(self, environment='prod'):
        self.credetial = {
            "user": tools.config.get('api_user'),
            "password": tools.config.get('api_password'),
            "api_key": tools.config.get('api_key_hotel'),
            "co_uid": False,
            "url_api": tools.config.get('url_api'),
        }
        self.cookie = False
        self.environment = environment

    def signin(self):
        req_post = self.credetial.copy()
        req_post.pop('url_api')
        res = self.send_request('signin', req_post)
        try:
            if res['http_code'] == 0:
                cookie = res['cookie']
                res = json.loads(res['response'])['result']
                if not res['error_code']:
                    res['cookie'] = cookie
                    self.cookie = cookie
                else:
                    res['error_code'] = res['error_code']
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

    def send_request(self, action, post=None, timeout=None):
        url = self.credetial['url_api'] + '/hotel/booking'
        if action in ('signin'):
            url = self.credetial['url_api'] + '/hotel/session'

        headers = {
            "Accept": "application/json,text/html,application/xml",
            "Content-Type": "application/json",
            'cookie': self.cookie,
            'action': action
        }
        return util.send_request_json(url, post=post, headers=headers, timeout=timeout)

    def get_record_by_api(self, req_post, api_context=None):
        self.credetial['co_uid'] = request.env.user.id
        self.signin()
        # Fixme: Auto sign if session expire
        res = self.send_request('get_vendor_content', req_post, timeout=60*5)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        res = json.loads(res['response'])['result']
        if res['error_code'] != 0:
            raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        return res

    def check_booking_status_by_api(self, req_post, api_context=None):
        self.credetial['co_uid'] = request.env.user.id
        self.signin()
        credential = self.credetial.copy()
        # Fixme: Auto sign if session expire
        res = self.send_request('check_booking_status', req_post, timeout=60*5)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        res = json.loads(res['response'])['result']
        if res['error_code'] != 0:
            raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        return res

    def check_booking_policy_by_api(self, req_post, api_context=None):
        self.credetial['co_uid'] = request.env.user.id
        self.signin()
        # Fixme: Auto sign if session expire
        res = self.send_request('check_booking_policy', req_post, timeout=60*5)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        res = json.loads(res['response'])['result']
        if res['error_code'] != 0:
            raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        return res

    def cancel_booking_by_api(self, req_post, api_context=None):
        self.credetial['co_uid'] = request.env.user.id
        self.signin()
        # Fixme: Auto sign if session expire
        res = self.send_request('cancel_booking', req_post, timeout=60*5)
        if res['http_code'] != 0:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        res = json.loads(res['response'])['result']
        if res['error_code'] != 0:
            raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        return res
