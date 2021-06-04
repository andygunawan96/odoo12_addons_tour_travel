from odoo import api, fields, models, _
import logging
import requests
import json
from ...tools.variables import ACC_TRANSPORT_TYPE, ACC_TRANSPORT_TYPE_REVERSE

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
        response = requests.post(url + '/api/method/jasaweb.rodex.insert_journal_entry', data=json.dumps(vals), headers=headers, cookies=cookies)
        if response.status_code == 200:
            _logger.info('Insert Success')
        else:
            _logger.info('Insert Failed')

        res = {
            'status_code': response.status_code,
            'content': response.content
        }
        _logger.info(res)

        if len(vals) > 0:
            temp_trans_type = vals[0].get('transport_type', '')
            temp_res_model = vals[0].get('transport_type') and ACC_TRANSPORT_TYPE_REVERSE.get(vals[0]['transport_type'], '') or ''
        else:
            temp_trans_type = ''
            temp_res_model = ''

        if response.status_code == 200:
            self.env['tt.accounting.history'].sudo().create({
                'request': vals,
                'response': res,
                'transport_type': temp_trans_type,
                'res_model': temp_res_model,
                'state': 'success'
            })
        else:
            self.env['tt.accounting.history'].sudo().create({
                'request': vals,
                'response': res,
                'transport_type': temp_trans_type,
                'res_model': temp_res_model,
                'state': 'failed'
            })
        return res