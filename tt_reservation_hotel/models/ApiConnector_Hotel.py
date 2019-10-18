from ...tools import util, ERR
import odoo.tools as tools
import json
from odoo.http import request
from ...tools.db_connector import DbConnector
API_CN_HOTEL = DbConnector()


class ApiConnectorHotels:
    token_permanent = ''
    user_cookie = ''

    def __init__(self, environment='prod'):
        authorization = tools.config.get('gateway_authorization', '')
        credential = util.decode_authorization(authorization)
        self.credetial = {
            "user": 'mob.it@rodextravel.tours',
            "password": '123',
            "api_key": '208413e7-3dee-4bed-9e16-5cfb9ce555a5',
            "co_uid": credential.get('uid', -1),
            "url_api": tools.config.get('gateway_url', ''),
        }
        self.cookie = 'None'
        self.environment = environment

    def signin(self):
        req_post = self.credetial.copy()
        req_post.pop('url_api')
        res = self.send_request('signin', req_post)
        try:
            if res['http_code'] == 200:
                res = json.loads(res['response'])['result']
                if not res['error_code']:
                    self.cookie = res['response']['signature']
                else:
                    res['error_code'] = res['error_code']
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

    def send_request(self, action, post=None, timeout=None):
        url = self.credetial['url_api'] + '/booking/hotel'
        if action in ['signin',]:
            url = '{}/session'.format(self.credetial['url_api'])

        headers = {
            "Accept": "application/json,text/html,application/xml",
            "Content-Type": "application/json",
            'signature': self.cookie or 'None',
            'action': action,
        }
        return util.send_request(url, data=post, headers=headers, timeout=timeout, is_json=True)

    def get_record_by_api(self, req_post, api_context=None):
        self.credetial['co_uid'] = request.env.user.id
        self.cookie = self.signin().get('cookie', False)
        # Fixme: Auto sign if session expire
        res = self.send_request('get_vendor_content', req_post, timeout=60*5)
        # res = API_CN_HOTEL.execute('', 'get_vendor_content', req_post)
        if res['error_code'] != 0:
            raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        res = json.loads(res['response'])['result']
        return res

    def check_booking_status_by_api(self, req_post, api_context=None):
        self.credetial['co_uid'] = request.env.user.id
        self.signin()
        # Fixme: Auto sign if session expire
        res = self.send_request('check_booking_status', req_post, timeout=60*5)
        if res['http_code'] != 200:
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
        if res['http_code'] != 200:
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
        if res['http_code'] != 200:
            raise Exception('%s %s' % (res['http_code'], res['error_msg']))
        res = json.loads(res['response'])['result']
        if res['error_code'] != 0:
            raise Exception('%s %s' % (res['error_code'], res['error_msg']))
        return res
