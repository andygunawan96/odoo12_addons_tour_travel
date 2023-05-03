from odoo import api, fields, models, _
import logging
import requests
import json
import base64
import time
from datetime import datetime

_logger = logging.getLogger(__name__)
# url = 'https://accurate.id'
# client_id = '55e778d2-f988-40b4-9723-b81f1dcce6ef'
# client_secret = 'f7195a4c40f1e38585bfc49efcad9a83'

# url_redirect_web = 'https://frontendinternal.rodextrip.com'
# username = 'rodexskytors@gmail.com'
# password = 'Ivanivanivan1!'
# database_id = 545518

class AccountingConnectorAccurate(models.Model):
    _name = 'tt.accounting.connector.accurate'
    _description = 'Accounting Connector Accurate'

    def acc_login(self, vals):
        url_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'accurate'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in Accurate Accounting Setup!')
        client_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'accurate'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'client_id')], limit=1)
        if not client_id_obj:
            raise Exception('Please provide a variable with the name "client_id" in Accurate Accounting Setup!')
        client_secret_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'accurate'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'client_secret')], limit=1)
        if not client_secret_obj:
            raise Exception('Please provide a variable with the name "client_secret" in Accurate Accounting Setup!')
        url_redirect_web_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'accurate'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'url_redirect_web')], limit=1)
        if not url_redirect_web_obj:
            raise Exception('Please provide a variable with the name "url_redirect_web" in Accurate Accounting Setup!')
        username_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'accurate'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'username')], limit=1)
        if not username_obj:
            raise Exception('Please provide a variable with the name "username" in Accurate Accounting Setup!')
        password_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'accurate'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'password')], limit=1)
        if not password_obj:
            raise Exception('Please provide a variable with the name "password" in Accurate Accounting Setup!')
        database_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'accurate'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'database_id')], limit=1)
        if not database_id_obj:
            raise Exception('Please provide a variable with the name "database_id" in Accurate Accounting Setup!')
        else:
            try:
                database_id = int(database_id_obj.variable_value)
            except:
                raise Exception('The "database_id" variable value in Accurate Accounting Setup must be integer!')

        url = url_obj.variable_value
        client_id = client_id_obj.variable_value
        client_secret = client_secret_obj.variable_value
        url_redirect_web = url_redirect_web_obj.variable_value
        username = username_obj.variable_value
        password = password_obj.variable_value

        ##page login get jsessionid
        res = requests.post('%s/oauth/authorize?client_id=%s&response_type=code&redirect_uri=%s&scope=customer_save customer_view customer_delete item_save glaccount_view glaccount_save glaccount_delete sales_invoice_view sales_invoice_save sales_receipt_save' % (url,client_id, url_redirect_web))

        res = requests.post(res.url)
        cookies = res.cookies.get_dict()
        if cookies == {}:
            url_to_cookie = res.url.split(';')[1]
            cookies[url_to_cookie.split('=')[0]] = url_to_cookie.split('=')[1]
        ##login
        data = {
            "email": username,
            "password": password
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) Gecko/20100101 Firefox/98.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "id,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://accurate.id",
            "Connection": "keep-alive",
            "Referer": "https://accurate.id/oauth/login.do",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1"
        }
        res_cookie = ';'.join(['%s=%s' % (key, val) for key, val in cookies.items()])
        headers.update({
            'Cookie': res_cookie
        })

        res = requests.post(url='%s/oauth/login' % url, data=data, headers=headers)

        time.sleep(15)
        ##ambil code
        code = res.request.url.split('code=')[1]

        ## get access_token
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": url_redirect_web
        }
        headers = {
            "Authorization": "Basic %s" % (str(base64.b64encode(("%s:%s" % (client_id, client_secret)).encode()), "utf-8"))
        }
        res = requests.post(url='https://account.accurate.id/oauth/token', data=data, headers=headers)
        response = json.loads(res.text)
        access_token = response['access_token']
        ## open db
        headers = {
            "Authorization": "Bearer %s" % (access_token)
        }
        data = {
            "id": database_id
        }
        res = requests.post(url='https://account.accurate.id/api/open-db.do', data=data, headers=headers)
        ## get X-Session-ID
        response = json.loads(res.text)
        x_session_id = response['session']
        url_db = response['host']
        headers.update({
            "X-Session-ID": x_session_id
        })
        return url_db, access_token, x_session_id


    ##BELUM GANTI
    def get_sales_order(self):
        url_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'accurate'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in Accurate Accounting Setup!')

        url = url_obj.variable_value
        # ses = requests.Session()
        cookies = False
        login_res = self.acc_login({})
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
        url_db, token, session_id = self.acc_login(vals)
        get_all_pax = self.get_customer(url_db, token, session_id)
        get_all_account = self.get_account(url_db, token, session_id)
        for rec in json.loads(vals):
            ## data_pax = for pax in get_all_pax
            pax = [pax for pax in get_all_pax if pax['name'] == rec['agent_id']]
            transaction_date = rec['date'].split('-')
            transaction_date.reverse()
            transaction_date = ['20', '04', '2022']
            if pax:
                id_customer = pax[0]['id']
            else:
                ##PAX TIDAK KETEMU ADD
                data = {
                    "name": rec['agent_id'],
                    "transaction_date": "/".join(transaction_date)
                }
                id_customer = self.add_customer(data,url_db, token, session_id)
                if id_customer:
                    pass
                else:
                    ##ERROR
                    pass

            if id_customer:
                ##ADD TRANSACTION

                ##CREATE ITEM
                data = {
                    "order_number": rec['name'],
                    "carrier_type": rec['transport_type'],
                    "total_nta": rec['NTA_amount_real'] if rec['credit'] != 0 else 0,
                    "grand_total": rec['credit'] - rec['debit']
                }
                item_number = self.create_item(data,url_db, token, session_id)
                if item_number:
                    ##create sales invoice
                    data = {
                        "customer_number": id_customer,
                        "item_number": item_number,
                        "grand_total": rec['credit'] - rec['debit'],
                        "name": rec['name'],
                        "date": "/".join(transaction_date)
                    }
                    sales_invoice_number = self.create_sales(data,url_db, token, session_id)
                    if sales_invoice_number:
                        data = {
                            "customer_number": id_customer,
                            "grand_total": rec['credit'] - rec['debit'],
                            "invoice_number": sales_invoice_number,
                            "date": "/".join(transaction_date)
                        }
                        payment_number = self.create_payment(data, url_db, token, session_id)
                    ##payment
                pass
            else:
                _logger.error('ERROR ID BELUM CREATE')
        response = {}
        # if login_res:
        #     cookies = login_res.cookies
        #
        # headers = {
        #     'Content-Type': 'text/text, */*; q=0.01',
        # }
        #
        # # res = util.send_request_json(self._get_web_hook('Sales%20Order'), post=vals, headers=headers)
        # response = requests.post(url + '/api/method/jasaweb.rodex.insert_journal_entry', data=vals, headers=headers, cookies=cookies)
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


    ##ACCURATE
    def add_customer(self, data, url_db, token, session_id):
        request = {
            # "name": "Testing IT",
            # "transDate": "22/02/2022",
            "name": data['name'],
            "transDate": data['transaction_date'],
        }

        headers= {
            "Authorization": "Bearer %s" % token,
            "X-Session-ID": session_id
        }
        _logger.info('Accurate Request Add Customer: %s', request)
        response = requests.post(url_db + '/accurate/api/customer/save.do', data=request, headers=headers)
        if response.status_code == 200:
            id = json.loads(response.text)['r']['id']
            return id
        return False

    def top_up(self, data, url_db, token, session_id):
        request = {
            # "name": "Testing IT",
            # "transDate": "22/02/2022",
            "name": data['name'],
            "transDate": data['transaction_date'],
            "id": data['id'],
            "detailOpenBalance": [
                {
                    "amount": 8000000,
                    "asOf": "22/02/2022",
                    "currencyCode": "IDR",
                    "description": "SALDO AWAL TESTING IT",
                    "rate": 1
                }
            ]
        }

        headers = {
            "Authorization": "Bearer %s" % token,
            "X-Session-ID": session_id
        }
        _logger.info('Accurate Request Top Up: %s', request)
        response = requests.post(url_db + '/accurate/api/customer/save.do', data=request, headers=headers)

    def get_customer(self, url_db, token, session_id):
        request = {
            "fields": "id,name,customerNo"
        }
        headers = {
            "Authorization": "Bearer %s" % token,
            "X-Session-ID": session_id
        }
        _logger.info('Accurate Request Get Customer: %s', request)
        response = requests.post(url_db + '/accurate/api/customer/list.do', data=request, headers=headers)
        data_response = []
        if response.status_code == 200:
            data_response = json.loads(response.text)['d']
        return data_response

    def create_account(self): ##HANYA PERTAMA KALI SAJA
        url_db, token, session_id = self.acc_login({})
        request = {
            "data": [
                {
                    "accountType": "OTHER_INCOME",
                    "asOf": datetime.now().strftime('%d/%m/%Y'),
                    "currency_code": "IDR",
                    "name": "SALDO PENJUALAN",
                    "no": "150",
                    "useUserRoleAccessListId": ""
                }, {
                    "accountType": "INVENTORY",
                    "asOf": datetime.now().strftime('%d/%m/%Y'),
                    "currency_code": "IDR",
                    "name": "Inventory",
                    "no": "151",
                    "useUserRoleAccessListId": ""
                }, {
                    "accountType": "REVENUE",
                    "asOf": datetime.now().strftime('%d/%m/%Y'),
                    "currency_code": "IDR",
                    "name": "Commission",
                    "no": "152",
                    "useUserRoleAccessListId": ""
                }, {
                    "accountType": "CASH_BANK",
                    "asOf": datetime.now().strftime('%d/%m/%Y'),
                    "currency_code": "IDR",
                    "name": "CASH",
                    "no": "153",
                    "useUserRoleAccessListId": ""
                }
            ]
        }

        headers = {
            "Authorization": "Bearer %s" % token,
            "X-Session-ID": session_id
        }
        _logger.info('Accurate Request Create Account: %s', request)
        response = requests.post(url_db + '/accurate/api/glaccount/bulk-save.do', json=request, headers=headers)

        ##SETELAH CREATE SETTING DI DEFAULT ACCURATE
        ## pengaturan, preferensi, akun perkiraan
        ## persediaan inventory
        ## penjualan saldo penjualan
        ## diskon penjualan commission
        return response

    def get_account(self, url_db, token, session_id):
        request = {
            "fields": "id,name,accountType",
            "sp": {
                "pageSize": 100,
                "sort": "id"
            }
        }
        headers = {
            "Authorization": "Bearer %s" % token,
            "X-Session-ID": session_id
        }

        _logger.info('Accurate Request Get Account: %s', request)
        response = requests.post(url_db + '/accurate/api/glaccount/list.do', json=request, headers=headers)
        data_response = []
        if response.status_code == 200:
            data_response = json.loads(response.text)['d']
        return data_response

    def create_item(self, data, url_db, token, session_id):
        ## CARI ACCOUNT
        request = {
            "itemType": "INVENTORY",
            "name": data['order_number'],
            "itemCategoryName": data['carrier_type'],
            "vendorPrice": data['total_nta'], ## TOTAL NTA
            "unitPrice": data['grand_total'], ##GRAND TOTAL
            "unit1Name": "Resv",
            "salesDiscountGlAccountNo": "152", ##NOMOR ACCOUNT
            "salesGlAccountNo": "150", ##NOMOR ACCOUNT
            "salesRetGlAccountNo": "150", ##NOMOR ACCOUNT
            "detailOpenBalance": [
                {
                    "unitRatio": "1",
                    "quantity": "1",
                    "unitCost": data['total_nta'] ##TOTAL NTA
                }
            ]
        }
        headers = {
            "Authorization": "Bearer %s" % token,
            "X-Session-ID": session_id
        }

        _logger.info('Accurate Request Create Item: %s', request)
        response = requests.post(url_db + '/accurate/api/item/save.do', json=request, headers=headers)
        if response.status_code == 200:
            return json.loads(response.text)['r']['no']
        return False

    def create_sales(self, data, url_db, token, session_id):
        ## CARI ITEM
        request = {
            "customerId": str(data['customer_number']),
            "detailExpense": [],
            "detailItem": [
                {
                    "itemNo": data['item_number'],
                    "unitPrice": data['grand_total'],
                    "detailSerialNumber": [],
                    "quantity": 1,
                    "itemCashDiscount": 0,
                    "salesmanListNumber": []
                }
            ],
            "description": data['name'],
            "cashDiscount": 0,
            "reverseInvoice": False,
            "taxDate": data['date'],
            "taxNumber": "",
            "transDate": data['date']
        }
        headers = {
            "Authorization": "Bearer %s" % token,
            "X-Session-ID": session_id
        }

        _logger.info('Accurate Request Create Sales: %s', request)
        response = requests.post(url_db + '/accurate/api/sales-invoice/save.do', json=request, headers=headers)
        if response.status_code == 200:
            return json.loads(response.text)['r']['number']
        return False


    def create_payment(self, data, url_db, token, session_id):
        ## CARI SALES
        request = {
            "bankNo": "153",
            "chequeAmount": int(data['grand_total']),
            "customerId": str(data['customer_number']),
            "detailInvoice": [
                {
                    "invoiceNo": data['invoice_number'],
                    "paymentAmount": int(data['grand_total'])
                }
            ],
            "transDate": data['date']
        }
        headers = {
            "Authorization": "Bearer %s" % token,
            "X-Session-ID": session_id
        }

        _logger.info('Accurate Request Create Payment: %s', request)
        response = requests.post(url_db + '/accurate/api/sales-receipt/save.do', json=request, headers=headers)

        return response
