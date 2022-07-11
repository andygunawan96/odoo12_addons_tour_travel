from odoo import api, fields, models, _
import logging
import requests
import json

_logger = logging.getLogger(__name__)
# url = 'https://accounting.rodextrip.com'
# usr = 'rodexapi'
# pwd = 'rodexapi'


class AccountingConnectorJasaweb(models.Model):
    _name = 'tt.accounting.connector.jasaweb'
    _description = 'Accounting Connector Jasaweb'

    def acc_login(self):
        url_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jasaweb'), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in Jasaweb Accounting Setup!')
        usr_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jasaweb'), ('variable_name', '=', 'usr')], limit=1)
        if not usr_obj:
            raise Exception('Please provide a variable with the name "usr" in Jasaweb Accounting Setup!')
        pwd_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jasaweb'), ('variable_name', '=', 'pwd')], limit=1)
        if not pwd_obj:
            raise Exception('Please provide a variable with the name "pwd" in Jasaweb Accounting Setup!')

        url = url_obj.variable_value
        usr = usr_obj.variable_value
        pwd = pwd_obj.variable_value
        auth = {'usr': usr, 'pwd': pwd}
        res = requests.post(url + '/api/method/login', data=auth)
        _logger.info(res)
        return res

    def get_sales_order(self):
        url_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'jasaweb'), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in Jasaweb Accounting Setup!')

        url = url_obj.variable_value
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
        url_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'jasaweb'), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in Jasaweb Accounting Setup!')

        url = url_obj.variable_value
        # ses = requests.Session()
        cookies = False
        login_res = self.acc_login()
        if login_res:
            cookies = login_res.cookies

        headers = {
            'Content-Type': 'text/text, */*; q=0.01',
        }
        req_data = self.request_parser(vals)
        # res = util.send_request_json(self._get_web_hook('Sales%20Order'), post=vals, headers=headers)
        response = requests.post(url + '/api/method/jasaweb.rodex.insert_journal_entry', data=req_data, headers=headers, cookies=cookies)
        res = self.response_parser(response)

        if res['status'] == 'success':
            _logger.info('Insert Success')
        else:
            _logger.info('Insert Failed')
        _logger.info(res)

        return res

    def request_parser(self, request):
        req = []
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        pay_method = ''
        if request['category'] == 'reservation':
            transport_type = request.get('provider_type_name', '')
            total_nta = request.get('total_nta', 0)
        elif request['category'] == 'refund':
            transport_type = 'Refund'
            total_nta = request.get('total_amount', 0)
        elif request['category'] == 'reschedule':
            transport_type = 'Reschedule'
            total_nta = request.get('total_amount', 0)
        elif request['category'] == 'top_up':
            transport_type = 'Top Up'
            total_nta = 0
            pay_method = request.get('acquirer_type', '') in ['payment_gateway', 'va'] and 'Payment Gateway' or 'Rodex Gateway'
        else:
            transport_type = ''
            total_nta = 0

        for rec in request['ledgers']:
            if rec['transaction_type'] == 1:
                trans_type = 'Top Up / Agent Payment'
            elif rec['transaction_type'] == 2:
                trans_type = 'Transport Booking'
            elif rec['transaction_type'] == 3:
                trans_type = 'Commission'
                if rec.agent_type_id.id == self.env.ref('tt_base.agent_type_ho').id:
                    trans_type += ' HO'
                else:
                    trans_type += ' Channel'
            elif rec.transaction_type == 4:
                trans_type = 'Refund'
            elif rec.transaction_type == 6:
                trans_type = 'Admin Fee'
            elif rec.transaction_type == 7:
                trans_type = 'Reschedule'
            else:
                trans_type = ''

            if request['category'] == 'refund' and trans_type == 'Admin Fee':
                trans_type = 'Refund Admin Fee'

            req.append({
                'reference_number': rec.get('ref', ''),
                'name': rec.get('name', ''),
                'debit': rec.get('debit', 0),
                'credit': rec.get('credit', 0),
                'currency_id': rec.get('currency_id', ''),
                'create_date': rec.get('create_date', ''),
                'date': rec.get('date', ''),
                'create_uid': rec.get('create_date', ''),
                'commission': 0.0,
                'description': rec.get('description', ''),
                'agent_id': rec.get('agent_id', 0),
                'company_sender': rec.get('agent_name', ''),
                'company_receiver': self.env.ref('tt_base.rodex_ho').name,
                'state': 'Done',
                'display_provider_name': rec.get('display_provider_name', ''),
                'pnr': rec.get('pnr', ''),
                'url_legacy': base_url + '/web#id=' + str(rec['id']) + '&model=tt.ledger&view_type=form',
                'transaction_type': trans_type,
                'transport_type': transport_type,
                'payment_method': pay_method,
                'NTA_amount_real': request['category'] == 'top_up' and rec.get('debit', 0) or total_nta,
                'payment_acquirer': request.get('payment_acquirer', 'CASH')
            })

        return json.dumps(req)

    def response_parser(self, response):
        res = {
            'status_code': response.status_code or 500,
            'content': response.content or ''
        }
        if res['status_code'] == 200:
            res.update({
                'status': 'success'
            })
        else:
            res.update({
                'status': 'failed'
            })
        if res.get('content'):
            try:
                res.update({
                    'content': res['content'].decode("UTF-8")
                })
            except (UnicodeDecodeError, AttributeError):
                pass
        return res
