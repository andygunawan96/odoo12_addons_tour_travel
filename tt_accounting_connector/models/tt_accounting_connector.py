from odoo import api, fields, models, _
import logging
import requests
import json

_logger = logging.getLogger(__name__)
url = 'http://accounting.rodextrip.com'


class AccountingConnector(models.Model):
    _name = 'tt.accounting.connector'
    _description = 'Accounting Connector'

    def acc_login(self):
        auth = {'usr': 'rodexapi', 'pwd': 'rodexapi'}
        res = requests.post(url + '/api/method/login', data=auth)
        _logger.info(res)
        return res

    def get_sales_order(self):
        # ses = requests.Session()
        cookies = False
        login_res = self.acc_login()
        if login_res:
            cookies = login_res.cookies

        headers = {
            'Content-Type': 'application/json, text/javascript, */*; q=0.01',
        }

        # res = util.send_request_json(self._get_web_hook('Sales%20Order'), post=vals, headers=headers)
        response = requests.post(url + '/api/method/jasaweb.rodex', headers=headers, cookies=cookies)
        res = response.content
        return res

    def add_sales_order(self, vals):
        # ses = requests.Session()
        cookies = False
        login_res = self.acc_login()
        if login_res:
            cookies = login_res.cookies

        headers = {
            'Content-Type': 'text/text, */*; q=0.01',
        }

        # res = util.send_request_json(self._get_web_hook('Sales%20Order'), post=vals, headers=headers)
        response = requests.post(url + '/api/method/jasaweb.rodex.insert_journal_entry', data=vals, headers=headers, cookies=cookies)
        if response.status_code == 200:
            _logger.info('Insert Success')
        else:
            _logger.info('Insert Failed')

        res = {
            'status_code': response.status_code or 500,
            'content': response.content or ''
        }
        _logger.info(res)

        return res
