from odoo import api, fields, models, _
import logging
import requests
import json
import base64
import time
from datetime import datetime, timedelta
from lxml import html


_logger = logging.getLogger(__name__)
# url = 'https://accurate.id'
# client_id = '55e778d2-f988-40b4-9723-b81f1dcce6ef'
# client_secret = 'f7195a4c40f1e38585bfc49efcad9a83'

# 'url_api', 'url_web', 'client_id', 'client_secret', 'email', 'password'

class AccountingConnectorAccurate(models.Model):
    _name = 'tt.accounting.connector.jurnalid'
    _description = 'Accounting Connector Jurnal Id'

    def testing_login(self):
        self.acc_login()

    def acc_login(self):
        url_api_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('variable_name', '=', 'url_api')], limit=1)
        if not url_api_obj:
            raise Exception('Please provide a variable with the name "url_api" in Accurate Accounting Setup!')

        url_web_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('variable_name', '=', 'url_web')], limit=1)
        if not url_web_obj:
            raise Exception('Please provide a variable with the name "url_web" in Accurate Accounting Setup!')

        client_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('variable_name', '=', 'client_id')],limit=1)
        if not client_id_obj:
            raise Exception('Please provide a variable with the name "client_id" in Accurate Accounting Setup!')

        client_secret_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('variable_name', '=', 'client_secret')],limit=1)
        if not client_secret_obj:
            raise Exception('Please provide a variable with the name "client_secret" in Accurate Accounting Setup!')

        email_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('variable_name', '=', 'email')], limit=1)
        if not email_obj:
            raise Exception('Please provide a variable with the name "client_secret" in Accurate Accounting Setup!')

        password_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('variable_name', '=', 'password')], limit=1)
        if not password_obj:
            raise Exception('Please provide a variable with the name "url_redirect_web" in Accurate Accounting Setup!')

        access_token_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('variable_name', '=', 'access_token')],limit=1)
        if not access_token_obj:
            raise Exception('Please provide a variable with the name "access_token" in Accurate Accounting Setup!')

        api_key_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('variable_name', '=', 'api_key')],limit=1)
        if not api_key_obj:
            raise Exception('Please provide a variable with the name "api_key" in Accurate Accounting Setup!')

        url_api = url_api_obj.variable_value
        url_web = url_web_obj.variable_value
        client_id = client_id_obj.variable_value ##dari https://developer.jurnal.id/developers/credentials
        client_secret = client_secret_obj.variable_value ##dari https://developer.jurnal.id/developers/credentials
        email = email_obj.variable_value
        password = password_obj.variable_value
        access_token = access_token_obj.variable_value
        api_key = api_key_obj.variable_value

        return {
            "api_key": api_key,
            "url_api": url_api,
            "access_token": access_token
        }

    def get_contact(self, data_login, vals):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token']
        }

        data = {}
        data_contact = vals.get('customer_parent_name') or vals['booker']['name']
        contact_name = ''
        index_page = 1
        while True:
            url = '%s/partner/core/api/v1/contacts?contact_index={"curr_page":%s,"selected_tab":1,"sort_asc":true,"show_archive":false}&access_token=%s' % (data_login['url_api'], index_page, data_login['access_token'])
            _logger.info('######REQUEST CONTACT#########\n%s' % json.dumps(data))
            res = requests.get(url, headers=headers, json=data)
            _logger.info('######RESPONSE CONTACT#########\n%s' % res.text)
            res_response = json.loads(res.text)
            contact_name = [d['display_name'] for d in res_response['contact_list']['contact_data']['person_data'] if d['display_name'] == data_contact]
            if res_response['contact_list']['contact_data']['max_page'] <= index_page or len(contact_name) > 0:
                if len(contact_name) > 0:
                    contact_name = contact_name[0]
                else:
                    contact_name = ''
                break
            index_page += 1
        if contact_name == '':
            contact_name = self.add_contact(data_login, data_contact)
        return contact_name

    def add_contact(self, data_login, data_contact):
        url = "%s/partner/core/api/v1/contacts" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token']
        }
        contact_group_id = self.get_contact_group(data_login)
        data = {
            "person": {
                "id": None,
                "display_name": data_contact,
                "title": None,
                "first_name": None,
                "middle_name": None,
                "last_name": None,
                "mobile": None,
                "identity_type": None,
                "identity_number": None,
                "email": None,
                "other_detail": None,
                "associate_company": None,
                "phone": None,
                "fax": None,
                "tax_no": None,
                "archive": False,
                "billing_address": None,
                "billing_address_no": None,
                "billing_address_rt": None,
                "billing_address_rw": None,
                "billing_address_post_code": None,
                "billing_address_kelurahan": None,
                "billing_address_kecamatan": None,
                "billing_address_kabupaten": None,
                "billing_address_provinsi": None,
                "address": None,
                "bank_account_details": [
                    {
                        "bank_name": None,
                        "bank_branch": "",
                        "bank_account_holder_name": "",
                        "bank_account_number": ""
                    }
                ],
                "default_ar_account_id": None,
                "default_ap_account_id": None,
                "disable_max_credit_limit": True,
                "disable_max_debit_limit": True,
                "max_credit_limit": None,
                "max_debit_limit": None,
                "term_id": None,
                "is_customer": True,
                "is_vendor": False,
                "is_employee": False,
                "is_others": False,
                "contact_group_ids": [
                  contact_group_id
                ],
                "people_type": "customer",
                "contact_group_names": [
                  "work",
                  "family"
                ]
            }
        }
        _logger.info('######REQUEST SEARCH CONTACT#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPONSE SEARCH CONTACT#########\n%s' % response.text)
        return json.loads(response.text)['person']['display_name']

    def get_contact_group(self, data_login):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token']
        }

        data = {}
        data_contact_group = 'Customer'
        contact_group_id = ''
        url = '%s/partner/core/api/v1/contact_groups' % (data_login['url_api'])
        _logger.info('######REQUEST PRODUCT#########\n%s' % json.dumps(data))
        response = requests.get(url, headers=headers, json=data)
        _logger.info('######RESPONSE CONTACT GROUP#########\n%s' % response.text)
        response_data = json.loads(response.text)
        contact_group_id = [d['id'] for d in response_data['contact_group'] if d['name'] == data_contact_group]
        if len(contact_group_id) > 0:
            contact_group_id = contact_group_id[0]
        if contact_group_id == '':
            contact_group_id = self.add_contact_group(data_login)
        return contact_group_id

    def add_contact_group(self, data_login):
        url = "%s/partner/core/api/v1/contacts" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token']
        }
        data = {
            "contact_group": {
                "name": "Customer",
                "company_id": 1,
                "contact_group_role": 1
            }
        }
        _logger.info('######REQUEST CONTACT GROUP#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPOSNE CONTACT GROUP#########\n%s' % json.dumps(response.text))
        return json.loads(response.text)['contact_group'][0]['id']

    def get_vendor(self, data_login, vendor_name):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token']
        }

        data = {}
        url = '%s/partner/core/api/v1/vendors' % (data_login['url_api'])
        _logger.info('######REQUEST SEARCH VENDOR#########\n%s' % json.dumps(data))
        response = requests.get(url, headers=headers, json=data)
        _logger.info('######RESPONSE SEARCH VENDOR#########\n%s' % response.text)
        response_data = json.loads(response.text)
        vendor_name_data = [d['display_name'] for d in response_data['vendors'] if d['display_name'] == vendor_name]
        if len(vendor_name_data) == 0:
            vendor_name = self.add_vendor(data_login, vendor_name)
        return vendor_name

    def add_vendor(self, data_login, vendor_name):
        url = "%s/partner/core/api/v1/vendors" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token']
        }
        data = {
            "vendor": {
                "title": "",
                "first_name": "",
                "middle_name": "",
                "last_name": "",
                "display_name": vendor_name,
                "associate_company": "",
                "billing_address": "",
                "address": "",
                "phone": "",
                "fax": "",
                "mobile": "",
                "email": "",
                "disable_max_credit_limit": True,
                "start_balance": datetime.now().strftime('DD-MM-YYYY'),
                "opening_balance": 0,
                "default_ar_account_name": "",
                "default_ap_account_name": "",
                "source": "",
                "tax_no": "",
                "other_detail": "",
                "custom_id": vendor_name
            }
        }
        _logger.info('######REQUEST ADD VENDOR#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPOSNE ADD PRODUCT#########\n%s' % response.text)
        return vendor_name

    ############
    def get_product(self, data_login, product_name):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }

        data = {}
        url = '%s/partner/core/api/v1/products' % (data_login['url_api'])
        _logger.info('######REQUEST SEARCH PRODUCT#########\n%s' % json.dumps(data))
        res = requests.get(url, headers=headers, json=data)
        _logger.info('######RESPONSE SEARCH PRODUCT#########\n%s' % res.text)
        res_response = json.loads(res.text)
        product_name_data = [d['name'] for d in res_response['products'] if d['name'] == product_name]
        if len(product_name_data) > 0:
            product_name = product_name_data[0]
        else:
            product_name = self.add_product(data_login, product_name)
        return product_name

    def add_product(self, data_login, product_name):
        url = "%s/partner/core/api/v1/contacts" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }
        data = {
            "product": {
                "name": "Ticket Perjalanan",
                "taxable_buy": True,
                "unit_name": "Paket",
                "sell_price_per_unit": "0",
                "custom_id": "",
                "track_inventory": "false",
                "description": "",
                "buy_price_per_unit": "0",
                "product_code": "",
                "is_bought": True,
                "buy_account_number": "",
                "buy_account_name": "",
                "is_sold": True,
                "sell_account_number": "",
                "sell_account_name": "",
                "taxable_sell": True,
                "inventory_asset_account_id": 0,
                "inventory_asset_account_name": "",
                "inventory_asset_account_number": "",
                "product_category_ids": [
                ],
                "product_bundles_attributes": [
                ],
                "bundle_costs_attributes": [
                ]
            }
        }
        _logger.info('######REQUEST ADD PRODUCT#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPONSE ADD PRODUCT#########\n%s' % response.text)
        return product_name

    def add_purchase(self, data_login, vals):
        url = "%s/partner/core/api/v1/purchase_invoices" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }

        invoice = ''
        for rec in vals['invoice_data']:
            if invoice != '':
                invoice = ', '
            invoice += rec
        for idx, ledger in enumerate(vals['ledgers'], start=1):
            passenger_data = ''
            desc = ''
            for provider_booking in vals['provider_bookings']:
                if ledger['pnr'] == provider_booking['pnr']:
                    for rec_ticket in provider_booking['tickets']:
                        if passenger_data != '':
                            passenger_data += ', '
                        passenger_data += rec_ticket['passenger']
                    pnr = provider_booking['pnr2'] if provider_booking['pnr2'] else provider_booking['pnr']
                    if desc != '':
                        desc += '; '
                    desc += "%s; Tiket Perjalanan %s-%s; %s; Atas Nama: %s" % (pnr, provider_booking['origin'], provider_booking['destination'],provider_booking['departure_date'].split(' ')[0], passenger_data)
                    break
            vendor_data = ledger['display_provider_name']
            ##### AMBIL VENDOR ###############
            vendor = self.get_vendor(data_login, vendor_data)
            ###################################

            ##### AMBIL PRODUCT ###############
            product_name = ''
            price = 0
            if ledger['debit'] != 0:
                product_name = 'Commission'
                price = ledger['debit']
                send = vals['is_send_commission']
            else:
                product_name = 'Tiket Perjalanan'
                price = ledger['credit']
                send = True
            if send:
                product = self.get_product(data_login, product_name)
                ###################################
                data = {
                    "purchase_invoice": {
                        "transaction_date": vals['issued_date'].split(' ')[0],
                        "transaction_lines_attributes": [
                            {
                                "quantity": 1,
                                "rate": price,
                                "discount": 0,
                                "product_name": product,
                                "description": desc
                            }
                        ],
                        "shipping_date": vals['issued_date'].split(' ')[0],
                        "shipping_price": 0,
                        "shipping_address": "",
                        "is_shipped": True,
                        "ship_via": "",
                        "reference_no": "%s - %s" % (invoice, product),
                        "tracking_no": "",
                        "address": "",
                        "term_name": "Cash",
                        "due_date": vals['issued_date'].split(' ')[0],
                        "refund_from_name": "",
                        "deposit": 0,
                        "discount_unit": 0,
                        "witholding_account_name": "",
                        "witholding_value": 0,
                        "witholding_type": "percent",
                        "discount_type_name": "percent",
                        "person_name": vendor,
                        "warehouse_name": "",
                        "warehouse_code": "",
                        "tags": [],
                        "email": "",
                        "message": desc,
                        "memo": desc,
                        "custom_id": "",
                        "source": "API",
                        "use_tax_inclusive": False,
                        "tax_after_discount": False
                    }
                }
                _logger.info('######REQUEST PURCHASE#########\n%s' % json.dumps(data))
                response = requests.post(url, headers=headers, json=data)
                _logger.info('######RESPONSE PURCHASE#########\n%s' % response.text)
        return 0

    def add_sales(self, data_login, vals, contact):
        url = "%s/partner/core/api/v1/sales_invoices" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }
        passenger_data = ''
        desc = ''
        for provider_bookings in vals['provider_bookings']:
            for rec_ticket in provider_bookings['tickets']:
                if passenger_data != '':
                    passenger_data += ', '
                passenger_data += rec_ticket['passenger']
            pnr = provider_bookings['pnr2'] if provider_bookings['pnr2'] else provider_bookings['pnr']
            if desc != '':
                desc += '; '
            desc += "%s; Tiket Perjalanan %s-%s; %s; Atas Nama: %s" % (
            pnr, provider_bookings['origin'], provider_bookings['destination'],
            provider_bookings['departure_date'].split(' ')[0], passenger_data)
            passenger_data = ''

        product = self.get_product(data_login, 'Tiket Perjalanan')

        due_date = (datetime.strptime(vals['issued_date'].split(' ')[0],'%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')

        data = {
            "sales_invoice": {
                "transaction_date": vals['issued_date'].split(' ')[0],
                "transaction_lines_attributes": [
                    {
                        "quantity": 1,
                        "rate": vals['total'] + vals['total_channel_upsell'] - vals['total_discount'],
                        "discount": 0,
                        "product_name": product,
                        "description": desc
                    }
                ],
                "shipping_date": vals['issued_date'].split(' ')[0],
                "shipping_price": 0,
                "shipping_address": "",
                "is_shipped": False,
                "ship_via": "",
                "reference_no": vals['order_number'],
                "tracking_no": "",
                "address": "",
                "term_name": "Billing cycle 30 days",
                "due_date": due_date,
                "deposit": 0,
                "discount_unit": 0,
                "witholding_value": 0,
                "witholding_type": "percent",
                "discount_type_name": "percent",
                "person_name": contact,
                "warehouse_name": "",
                "warehouse_code": "",
                "tags": [],
                "email": vals['booker'].get('email', ''),
                "message": desc,
                "memo": desc,
                "custom_id": "",
                "source": "API",
                "use_tax_inclusive": False,
                "tax_after_discount": False
            }
        }
        _logger.info('######REQUEST SALES#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPONSE SALES#########\n%s' % response.text)
        return 0


    def add_sales_order(self, vals):
        cookies = False
        data_login = self.acc_login()

        ##### AMBIL CONTACT ###############
        contact = self.get_contact(data_login, vals)
        ###################################

        ####### CREATE PURCHASE INVOICE ##########
        self.add_purchase(data_login, vals)
        ###################################

        ####### CREATE SALES INVOICE ##########
        self.add_sales(data_login, vals, contact)
        ###################################


        res = self.response_parser()
        return res

    def response_parser(self):
        res = {
            'status_code': 'success',
            'content': ''
        }
        return res
