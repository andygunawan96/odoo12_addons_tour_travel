from ...tools import util, ERR
import odoo.tools as tools
import json
from odoo.http import request
from datetime import datetime


class ApiConnectorActivity:

    token_permanent = ''
    user_cookie = ''

    #  DEMO
    # def __init__(self, environment='demo'):

    #  PROD
    def __init__(self, environment='prod'):
        self.credential = {
            "user": tools.config.get('api_user'),
            "password": tools.config.get('api_password'),
            "api_key": tools.config.get('api_key_activity'),
            "co_uid": False,
            "url_api": tools.config.get('url_api'),
        }
        self.environment = environment

    def send_request(self, action, post=None, cookie=None, timeout=60):
        url = '{}/booking/activity'.format(self.credential['url_api'])
        headers = {
            "Accept": "application/json,text/html,application/xml",
            "Content-Type": "application/json",
            'cookie': cookie,
            'action': action
        }
        return util.send_request(url, data=post, headers=headers, timeout=timeout)

    def signin(self, co_uid=None):
        try:
            self.credential['co_uid'] = request.session.uid
        except:
            self.credential['co_uid'] = co_uid
        req_post = self.credential.copy()
        # req_post.pop('url_sess')
        # req_post.pop('url_book')
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
                'error_msg': ERR.get_error(err),
                'response': ''
            }
        return res

    def update_booking(self, req_post, cookie):
        counter = 0
        while not cookie and counter < 10:
            cookie = self.signin().get('cookie', False)
            counter += 1

        res = self.send_request('update_booking', req_post, cookie, timeout=60 * 10)
        try:
            if res['http_code'] == 0:
                res = json.loads(res['response'])['result']
            else:
                res['error_code'] = res['http_code']
                res['error_msg'] = 'Connection to provider: {}'.format('activity')

        except Exception:
            res = {
                'error_code': 500,
                'error_msg': 'Error while send update booking request'
            }
        return res

    def get_vouchers(self, req_post, cookie):
        counter = 0
        while not cookie and counter < 10:
            cookie = self.signin().get('cookie', False)
            counter += 1

        res = self.send_request('get_vouchers', req_post, cookie, timeout=60 * 10)
        try:
            if res['http_code'] == 0:
                res = json.loads(res['response'])['result']
            else:
                res['error_code'] = res['http_code']
                res['error_msg'] = 'Connection to provider: {}'.format('activity')

        except Exception:
            err = 3013
            res = {
                'error_code': err,
                'error_msg': ERR.get_error(err)['error_msg'],
            }
        return res

    def get_vouchers_api(self, req_post, co_uid, cookie):
        counter = 0
        while not cookie and counter < 10:
            cookie = self.signin(co_uid).get('cookie', False)
            counter += 1

        res = self.send_request('get_vouchers', req_post, cookie, timeout=60 * 10)
        try:
            if res['http_code'] == 0:
                res = json.loads(res['response'])['result']
            else:
                res['error_code'] = res['http_code']
                res['error_msg'] = 'Connection to provider: {}'.format('activity')

        except Exception:
            err = 3013
            res = {
                'error_code': err,
                'error_msg': ERR.get_error(err)['error_msg'],
            }
        return res

    def get_booking(self, req, cookie):
        counter = 0
        while not cookie and counter < 10:
            cookie = self.signin().get('cookie', False)
            counter += 1

        req_post = {
            'order_number': req.get('order_number', ''),
            'order_id': req.get('order_id', ''),
            'provider': req.get('provider', ''),
            'uuid': req.get('uuid', ''),
            'pnr': req.get('pnr', ''),
        }

        res = self.send_request('get_booking', req_post, cookie, timeout=60 * 10)
        try:
            if res['http_code'] == 0:
                res = json.loads(res['response'])['result']
            else:
                res['error_code'] = res['http_code']
                res['error_msg'] = 'Connection to provider: {}'.format('activity')

        except Exception:
            res = {
                'error_code': 500,
                'error_msg': 'Error while send get booking request'
            }

        return res

    def send_product_analytics(self, req, cookie):
        counter = 0
        while not cookie and counter < 10:
            cookie = self.signin().get('cookie', False)
            counter += 1

        res = self.send_request('send_product_analytics', req, cookie, timeout=60 * 10)
        try:
            if res['http_code'] == 0:
                res = json.loads(res['response'])['result']
            else:
                res['error_code'] = res['http_code']
                res['error_msg'] = 'Connection to provider: {}'.format('activity')
        except Exception:
            err = 3011
            res = {
                'error_code': err,
                'error_msg': ERR.get_error(err)['error_msg'],
                'response': 'REQUEST : {}'.format(json.dumps(req))
            }
        if res['error_code'] != 0:
            # Fixme: Terkadang error yang tidak terkendalikan (Loading terus)
            res['error_msg'] = res['error_msg'] and res[
                'error_msg'] or 'Search send_request ERROR (Provider : {})'.format('activity')

        return res

    def get_pricing(self, req, cookie):
        counter = 0
        while not cookie and counter < 10:
            cookie = self.signin().get('cookie', False)
            counter += 1

        req_post = {
            'product_type_uuid': req.get('product_type_uuid', ''),
            'date_start': req.get('date_start', ''),
            'date_end': req.get('date_end', ''),
            'provider': req.get('provider', ''),
        }

        res = self.send_request('get_pricing', req_post, cookie, timeout=60 * 10)
        try:
            if res['http_code'] == 0:
                res = json.loads(res['response'])['result']
            else:
                res['error_code'] = res['http_code']
                res['error_msg'] = 'Connection to provider: {}'.format('activity')

        except Exception:
            res = {
                'error_code': 500,
                'error_msg': 'Error while send get booking request'
            }

        return res

    def resend_voucher(self, req, cookie):
        counter = 0
        while not cookie and counter < 10:
            cookie = self.signin().get('cookie', False)
            counter += 1

        res = self.send_request('resend_voucher', req, cookie, timeout=60 * 10)
        try:
            if res['http_code'] == 0:
                res = json.loads(res['response'])['result']
            else:
                res['error_code'] = res['http_code']
                res['error_msg'] = 'Connection to provider: {}'.format('activity')

        except Exception:
            res = {
                'error_code': 500,
                'error_msg': 'Error while send get booking request'
            }

        return res
