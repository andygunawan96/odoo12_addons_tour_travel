from odoo import api, fields, models, _
import logging
import requests
import json
import base64
import time
from datetime import datetime, timedelta
from lxml import html
import traceback


_logger = logging.getLogger(__name__)
# url = 'https://accurate.id'
# client_id = '55e778d2-f988-40b4-9723-b81f1dcce6ef'
# client_secret = 'f7195a4c40f1e38585bfc49efcad9a83'

# 'url_api', 'url_web', 'client_id', 'client_secret', 'email', 'password'

class AccountingConnectorJurnalID(models.Model):
    _name = 'tt.accounting.connector.jurnalid'
    _description = 'Accounting Connector Jurnal Id'

    def testing_login(self):
        self.acc_login({})

    def acc_login(self, vals):
        url_api_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'url_api')], limit=1)
        if not url_api_obj:
            raise Exception('Please provide a variable with the name "url_api" in Accurate Accounting Setup!')

        url_web_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'url_web')], limit=1)
        if not url_web_obj:
            raise Exception('Please provide a variable with the name "url_web" in Accurate Accounting Setup!')

        client_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'client_id')],limit=1)
        if not client_id_obj:
            raise Exception('Please provide a variable with the name "client_id" in Accurate Accounting Setup!')

        client_secret_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'client_secret')],limit=1)
        if not client_secret_obj:
            raise Exception('Please provide a variable with the name "client_secret" in Accurate Accounting Setup!')

        access_token_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'access_token')],limit=1)
        if not access_token_obj:
            raise Exception('Please provide a variable with the name "access_token" in Accurate Accounting Setup!')

        api_key_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'jurnalid'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'api_key')],limit=1)
        if not api_key_obj:
            raise Exception('Please provide a variable with the name "api_key" in Accurate Accounting Setup!')

        url_api = url_api_obj.variable_value
        url_web = url_web_obj.variable_value
        client_id = client_id_obj.variable_value ##dari https://developer.jurnal.id/developers/credentials
        client_secret = client_secret_obj.variable_value ##dari https://developer.jurnal.id/developers/credentials
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
        # _logger.info(json.dumps(vals))
        data_contact = vals.get('customer_parent_name') or vals['booker']['name'] if vals.get('customer_parent_type_id') and vals['customer_parent_type_id'].get('code') == 'cor' else vals['booker']['name']
        contact_name = ''
        index_page = 1
        while True:
            url = '%s/partner/core/api/v1/contacts?contact_index={"curr_page":%s,"selected_tab":1,"sort_asc":true,"show_archive":false}&access_token=%s' % (data_login['url_api'], index_page, data_login['access_token'])
            _logger.info('######REQUEST SEARCH CONTACT#########\n%s' % json.dumps(data))
            res = requests.get(url, headers=headers, json=data)
            _logger.info('######RESPONSE SEARCH CONTACT#########\n%s' % res.text)
            res_response = json.loads(res.text)
            contact_name = [d['display_name'] for d in res_response['contact_list']['contact_data']['person_data'] if d['display_name'].upper() == data_contact.upper()]
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
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
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
        _logger.info('######REQUEST ADD CONTACT#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPONSE ADD CONTACT#########\n%s' % response.text)
        try:
            ## sucess create contact
            return json.loads(response.text)['person']['display_name']
        except:
            ## name already use
            return data_contact

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
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }
        data = {
            "contact_group": {
                "name": "Customer",
                "company_id": 1,
                "contact_group_role": 1
            }
        }
        _logger.info('######REQUEST ADD CONTACT GROUP#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPOSNE ADD CONTACT GROUP#########\n%s' % json.dumps(response.text))
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
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
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
    def get_product(self, data_login, product_name, unit_product="Paket"):
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
            product_name = self.add_product(data_login, product_name, unit_product)
        return product_name

    def add_product(self, data_login, product_name, unit_name):
        url = "%s/partner/core/api/v1/products" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }
        data = {
            "product": {
                "name": product_name,
                "taxable_buy": True,
                "unit_name": unit_name,
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
                "product_category_ids": [],
                "product_bundles_attributes": [],
                "bundle_costs_attributes": []
            }
        }
        _logger.info('######REQUEST ADD PRODUCT#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPONSE ADD PRODUCT#########\n%s' % response.text)
        return product_name

    def search_tags(self, data_login, tag_name):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }

        data = {}
        url = '%s/partner/core/api/v1/tags' % (data_login['url_api'])
        _logger.info('######REQUEST SEARCH TAGS#########\n%s' % json.dumps(data))
        res = requests.get(url, headers=headers, json=data)
        _logger.info('######RESPONSE SEARCH PRODUCT#########\n%s' % res.text)
        res_response = json.loads(res.text)
        tags_name_data = [d['name'] for d in res_response['tags'] if d['name'] == tag_name]
        if len(tags_name_data) > 0:
            tag_name = tags_name_data[0]
        else:
            tag_name = self.add_tag(data_login, tag_name)
        return tag_name

    def add_tag(self, data_login, tag_name):
        url = "%s/partner/core/api/v1/tags" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }
        data = {
            "tag": {
                "name": tag_name,
                "custom_id": tag_name
            }
        }
        _logger.info('######REQUEST ADD TAG#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPONSE ADD TAG#########\n%s' % response.text)
        return tag_name

    def add_purchase(self, data_login, vals):
        if len(vals['ledgers']) > 0:
            url = "%s/partner/core/api/v1/purchase_invoices" % data_login['url_api']
            headers = {
                "Content-Type": "application/json",
                "Authorization": "bearer %s" % data_login['access_token'],
                "api_key": data_login['api_key']
            }

            invoice = ''
            for rec in vals['invoice_data']:
                if invoice != '':
                    invoice += ', '
                invoice += rec
            pnr_list = {}
            for idx, ledger in enumerate(vals['ledgers'], start=1):
                if not pnr_list.get(ledger['pnr']):
                    pnr_list[ledger['pnr']] = []
                pnr_list[ledger['pnr']].append(ledger)


            for pnr in pnr_list:
                passenger_data = ''
                desc = ''
                list_desc = []
                for provider_booking in vals['provider_bookings']:
                    ## HOTEL
                    if vals['provider_type_name'] == 'Hotel':
                        for rec_ticket in provider_booking['passengers']:
                            if passenger_data != '':
                                passenger_data += ', '
                            passenger_data += rec_ticket['name']
                        for room in provider_booking['rooms']:
                            if pnr == room['prov_issued_code']:
                                desc = "%s; %s; %s-%s; %s; %s; Atas Nama: %s" % (pnr, provider_booking['hotel_name'], datetime.strptime(provider_booking['checkin_date'], '%Y-%m-%d').strftime('%d %b %Y'), datetime.strptime(provider_booking['checkout_date'], '%Y-%m-%d').strftime('%d %b %Y'),room['room_name'], room['meal_type'], passenger_data)
                                list_desc.append({
                                    "price": room['room_rate'] / len(room['dates']) - ((provider_booking['agent_commission'] + provider_booking['ho_commission']) / (len(provider_booking['rooms']) * len(room['dates']))),
                                    "desc": desc,
                                    "quantity": len(room['dates'])
                                })
                        desc = ''
                        vendor_data = provider_booking['provider_code']
                    ##AIRLINE TRAIN BUS
                    elif vals['provider_type_name'] in ['Airline', 'Train', 'Bus']:
                        if pnr == provider_booking['pnr']:
                            # for rec_ticket in provider_booking['tickets']:
                            #     if passenger_data != '':
                            #         passenger_data += ', '
                            #     passenger_data += rec_ticket['passenger']
                            # if desc != '':
                            #     desc += '; '
                            # desc += "%s; Tiket Perjalanan %s-%s; %s; Atas Nama: %s" % (pnr, provider_booking['origin'], provider_booking['destination'], provider_booking['departure_date'].split(' ')[0], passenger_data)

                            journey_type = ''
                            journey_text = ''
                            for idx, journey in enumerate(provider_booking['journeys']):
                                if idx == 0:
                                    journey_text += '%s-%s %s' % (journey['origin'], journey['destination'], journey['departure_date'].split(' ')[0])
                                    journey_type = 'ONEWAY'
                                else:
                                    journey_text += ';%s-%s %s' % (journey['origin'], journey['destination'], journey['departure_date'].split(' ')[0])
                                    if journey_text.split('-')[-1:] == journey['destination']:
                                        journey_type = 'MULTICITY'
                                    else:
                                        journey_type = 'RETURN'


                            for rec_ticket in provider_booking['tickets']:
                                desc += "%s; Tiket Perjalanan %s %s; Atas Nama: %s" % (pnr, journey_type, journey_text, rec_ticket['passenger'])
                                list_desc.append({
                                    "price": rec_ticket['total_nta'],
                                    "desc": desc,
                                    "quantity": 1
                                })
                            desc = ''
                            vendor_data = provider_booking['provider']
                    ## PPOB
                    elif vals['provider_type_name'] == 'PPOB':
                        if pnr == provider_booking['pnr']:
                            if desc != '':
                                desc += '; '
                            desc += "%s; %s; %s; %s;" % (provider_booking['customer_number'], provider_booking['carrier_name'], provider_booking['transaction_code'], datetime.strptime(vals['issued_date'][:10], '%Y-%m-%d').strftime('%d %b %Y'))
                            vendor_data = provider_booking['provider']

                    ## ACTIVITY
                    elif vals['provider_type_name'] == 'Activity':
                        if pnr == provider_booking['pnr']:
                            activity_name = provider_booking['activity_details'][0]['activity']
                            visit_date = datetime.strptime(provider_booking['activity_details'][0]['visit_date'],'%Y-%m-%d').strftime('%d %b %Y')
                            for rec_ticket in provider_booking['tickets']:
                                if passenger_data != '':
                                    passenger_data += ', '
                                desc = "%s; %s; %s; Atas Nama: %s" % (pnr, activity_name, visit_date, rec_ticket['passenger'])
                                list_desc.append({
                                    "price": rec_ticket['total_nta'],
                                    "desc": desc,
                                    "quantity": 1
                                })
                            desc = ''
                            vendor_data = provider_booking['provider']

                    ## TOUR
                    elif vals['provider_type_name'] == 'Tour':
                        if pnr == provider_booking['pnr']:
                            for rec_ticket in provider_booking['tickets']:
                                if passenger_data != '':
                                    passenger_data += ', '
                                passenger_data += rec_ticket['passenger']
                            if desc != '':
                                desc += '; '
                            desc += "%s; Tour %s; %s - %s; Atas Nama: %s" % (pnr, provider_booking['tour_name'], datetime.strptime(str(provider_booking['departure_date'])[:10], '%Y-%m-%d').strftime('%d %b %Y'), datetime.strptime(str(provider_booking['arrival_date'])[:10], '%Y-%m-%d').strftime('%d %b %Y'), passenger_data)
                            vendor_data = provider_booking['provider']

                    ## VISA PASSPORT
                    elif vals['provider_type_name'] == 'Visa':
                        if pnr == provider_booking['pnr']:
                            for pax in provider_booking['passengers']:
                                if passenger_data != '':
                                    passenger_data += ', '
                                passenger_data += pax['passenger']
                            if desc != '':
                                desc += '; '
                            desc += "%s; VISA %s; Departure Date: %s; Atas Nama: %s" % (pnr, provider_booking['country'], datetime.strptime(str(provider_booking['departure_date'])[:10], '%d/%m/%Y').strftime('%d %b %Y'), passenger_data)
                            vendor_data = provider_booking['provider']
                    passenger_data = ''

                ##### AMBIL VENDOR ###############
                vendor = self.get_vendor(data_login, vendor_data)
                ###################################

                ##### AMBIL PRODUCT ###############
                product_name = ''
                price = 0
                for idy,ledger in enumerate(pnr_list[pnr], start=1):
                    send = False
                    price = 0
                    transaction_lines_attributes_list = []
                    unit_product = 'Paket'
                    if vals['agent_id'] == ledger['agent_id']:
                        if ledger['debit'] != 0:
                            product_name = 'Tiket Perjalanan'
                            price = ledger['debit']
                            send = vals['is_send_commission']
                        else:
                            for provider_booking in vals['provider_bookings']:
                                if not provider_booking.get('is_sent') and pnr == provider_booking['pnr']:
                                    price += provider_booking['total_price']
                                    provider_booking['is_sent'] = True
                            if price != 0:
                                if vals['provider_type_name'] == 'Hotel':
                                    product_name = 'Hotel'
                                    unit_product = 'Night'
                                elif vals['provider_type_name'] in ['Airline', 'Train', 'Bus']:
                                    product_name = 'Tiket Perjalanan'
                                elif vals['provider_type_name'] in ['PPOB']:
                                    product_name = 'PPOB'
                                elif vals['provider_type_name'] in ['Tour']:
                                    product_name = 'TOUR'
                                elif vals['provider_type_name'] == 'Activity':
                                    product_name = 'Jasa Lainnya'
                                elif vals['provider_type_name'] == 'Visa':
                                    product_name = 'VISA'
                                elif vals['provider_type_name'] == 'Passport':
                                    product_name = 'Paspor'
                                product = self.get_product(data_login, product_name, unit_product)
                                if len(list_desc) == 0:
                                    transaction_lines_attributes_list.append({
                                        "quantity": 1,
                                        "rate": price,
                                        "discount": 0,
                                        "product_name": product,
                                        "description": desc
                                    })
                                else:
                                    desc = ''
                                    for list_desc_data in list_desc:
                                        transaction_lines_attributes_list.append({
                                            "quantity": list_desc_data['quantity'],
                                            "rate": list_desc_data['price'],
                                            "discount": 0,
                                            "product_name": product,
                                            "description": list_desc_data['desc']
                                        })
                                        if desc:
                                            desc += '; '
                                        desc += list_desc_data['desc']
                                send = True
                    if send:
                        product = self.get_product(data_login, product_name, unit_product)
                        ###################################
                        issued_date = vals['issued_date'].split(' ')[0]
                        data = {
                            "purchase_invoice": {
                                "transaction_date": issued_date,
                                "transaction_lines_attributes": transaction_lines_attributes_list,
                                "shipping_date": issued_date,
                                "shipping_price": 0,
                                "shipping_address": "",
                                "is_shipped": True,
                                "ship_via": "",
                                "reference_no": "%s - %s" % (invoice, product),
                                "tracking_no": "",
                                "address": "",
                                "term_name": "Cash",
                                "due_date": issued_date,
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
                                "message": "",
                                "memo": desc,
                                "custom_id": "",
                                "source": "API",
                                "use_tax_inclusive": False,
                                "tax_after_discount": False,
                                "status": "approved"
                            }
                        }
                        _logger.info('######REQUEST PURCHASE#########\n%s' % json.dumps(data))
                        response = requests.post(url, headers=headers, json=data)
                        _logger.info('######RESPONSE PURCHASE#########\n%s' % response.text)
                        if not json.loads(response.text).get('purchase_invoice'):
                            _logger.error('######ERROR ADD PURCHASE JURNAL ID %s#########\n' % vals['order_number'])
                            raise Exception(500, 'Error add purchase')
                        price = 0
        else:
            _logger.info('###JurnalID, Already sent to vendor accounting####')
        return 0

    def add_sales(self, data_login, vals, contact):
        if len(vals['ledgers']) > 0:
            url = "%s/partner/core/api/v1/sales_invoices" % data_login['url_api']
            headers = {
                "Content-Type": "application/json",
                "Authorization": "bearer %s" % data_login['access_token'],
                "api_key": data_login['api_key']
            }
            passenger_data = ''
            desc = ''
            list_desc = []
            is_user_ho = False
            if vals.get('agent_id'):
                agent_obj = self.env['tt.agent'].browse(int(vals['agent_id']))
                if agent_obj and agent_obj.is_ho_agent:
                    is_user_ho = True
            ## AIRLINE & TRAIN
            for provider_booking in vals['provider_bookings']:
                ## HOTEL
                if vals['provider_type_name'] == 'Hotel':
                    for rec_ticket in provider_booking['passengers']:
                        if passenger_data != '':
                            passenger_data += ', '
                        passenger_data += rec_ticket['name']
                    pnr = provider_booking['pnr']
                    for room in provider_booking['rooms']:
                        if pnr == room['prov_issued_code']:
                            desc = "%s; %s; %s-%s; %s; %s; Atas Nama: %s" % (pnr, provider_booking['hotel_name'], datetime.strptime(provider_booking['checkin_date'], '%Y-%m-%d').strftime('%d %b %Y'),datetime.strptime(provider_booking['checkout_date'], '%Y-%m-%d').strftime('%d %b %Y'), room['room_name'], room['meal_type'], passenger_data)
                            price = 0
                            if is_user_ho:
                                price = (room['room_rate'] / len(room['dates'])) + (vals['total_channel_upsell'] / ((len(provider_booking['rooms'] * len(vals['provider_bookings']))) * len(room['dates']))) - (vals['total_discount'] / len(provider_booking['rooms']))
                            else:
                                ## - total commission + commission HO karena dapet harga full
                                price = (room['room_rate'] / len(room['dates'])) - (vals['total_discount'] / len(provider_booking['rooms'])) + ((provider_booking['ho_commission']) / len(provider_booking['rooms']))
                            list_desc.append({
                                "price": price,
                                "desc": desc,
                                "quantity": len(room['dates'])
                            })
                    desc = ''

                ##AIRLINE TRAIN BUS
                elif vals['provider_type_name'] in ['Airline', 'Train', 'Bus']:
                    pnr = provider_booking['pnr'] if provider_booking['pnr'] else provider_booking['pnr2']
                    journey_type = ''
                    journey_text = ''
                    for idx, journey in enumerate(provider_booking['journeys']):
                        if idx == 0:
                            journey_text += '%s-%s %s' % (
                            journey['origin'], journey['destination'], journey['departure_date'].split(' ')[0])
                            journey_type = 'ONEWAY'
                        else:
                            journey_text += ';%s-%s %s' % (
                            journey['origin'], journey['destination'], journey['departure_date'].split(' ')[0])
                            if journey_text.split('-')[-1:] == journey['destination']:
                                journey_type = 'MULTICITY'
                            else:
                                journey_type = 'RETURN'

                    for rec_ticket in provider_booking['tickets']:
                        desc = "%s; Tiket Perjalanan %s %s; Atas Nama: %s" % (pnr, journey_type, journey_text, rec_ticket['passenger'])
                        price = 0
                        if is_user_ho:
                            price = rec_ticket['total_nta'] + rec_ticket['total_commission'] - (vals['total_discount'] / (len(provider_booking['tickets']) * len(provider_booking['tickets'])))
                        else:
                            price = rec_ticket['total_nta'] - (vals['total_discount'] / (len(provider_booking['tickets']) * len(provider_booking['tickets']))) + rec_ticket['ho_commission']
                        list_desc.append({
                            "price": price,
                            "desc": desc,
                            "quantity": 1
                        })
                    desc = ''
                    vendor_data = provider_booking['provider']


                    # for rec_ticket in provider_booking['tickets']:
                    #     if passenger_data != '':
                    #         passenger_data += ', '
                    #     passenger_data += rec_ticket['passenger']
                    # pnr = provider_booking['pnr'] if provider_booking['pnr'] else provider_booking['pnr2']
                    # if desc != '':
                    #     desc += '; '
                    # desc += "%s; Tiket Perjalanan %s-%s; %s; Atas Nama: %s" % (
                    # pnr, provider_booking['origin'], provider_booking['destination'],
                    # provider_booking['departure_date'].split(' ')[0], passenger_data)
                ## PPOB
                elif vals['provider_type_name'] == 'PPOB':
                    pnr = provider_booking['pnr'] if provider_booking['pnr'] else provider_booking['pnr2']
                    desc += "%s; %s; %s; %s;" % (provider_booking['customer_number'], provider_booking['carrier_name'],provider_booking['transaction_code'],datetime.strptime(vals['issued_date'][:10], '%Y-%m-%d').strftime('%d %b %Y'))
                    vendor_data = provider_booking['provider']

                ## ACTIVITY
                elif vals['provider_type_name'] == 'Activity':
                    activity_name = provider_booking['activity_details'][0]['activity']
                    visit_date = datetime.strptime(provider_booking['activity_details'][0]['visit_date'],'%Y-%m-%d').strftime('%d %b %Y')
                    pnr = provider_booking['pnr'] if provider_booking['pnr'] else provider_booking['pnr2']
                    for rec_ticket in provider_booking['tickets']:
                        desc = "%s; %s; %s; Atas Nama: %s" % (pnr, activity_name, visit_date, rec_ticket['passenger'])
                        price = 0
                        if is_user_ho:
                            price = rec_ticket['total_nta'] + rec_ticket['total_commission'] - (vals['total_discount'] / len(provider_booking['tickets']))
                        else:
                            price = rec_ticket['total_nta'] - (vals['total_discount']/len(provider_booking['tickets'])) + (rec_ticket['ho_commission'])
                        list_desc.append({
                            "price": price,
                            "desc": desc,
                            "quantity": 1
                        })
                    desc = ''
                    vendor_data = provider_booking['provider']

                ## TOUR
                elif vals['provider_type_name'] == 'Tour':
                    for rec_ticket in provider_booking['tickets']:
                        if passenger_data != '':
                            passenger_data += ', '
                        passenger_data += rec_ticket['passenger']
                    if desc != '':
                        desc += '; '
                    pnr = provider_booking['pnr'] if provider_booking['pnr'] else provider_booking['pnr2']
                    desc += "%s; TOUR %s; %s - %s; Atas Nama: %s" % (pnr, provider_booking['tour_name'],datetime.strptime(str(provider_booking['departure_date'])[:10], '%Y-%m-%d').strftime('%d %b %Y'), datetime.strptime(str(provider_booking['arrival_date'])[:10], '%Y-%m-%d').strftime('%d %b %Y'), passenger_data)

                ## VISA PASSPORT
                elif vals['provider_type_name'] == 'Visa':
                    for pax in provider_booking['passengers']:
                        if passenger_data != '':
                            passenger_data += ', '
                        passenger_data += pax['passenger']
                    if desc != '':
                        desc += '; '
                    pnr = provider_booking['pnr'] if provider_booking['pnr'] else provider_booking['pnr2']
                    desc += "%s; VISA %s; Departure Date: %s; Atas Nama: %s" % (pnr, provider_booking['country'],datetime.strptime(str(provider_booking['departure_date'])[:10], '%d/%m/%Y').strftime('%d %b %Y'), passenger_data)
                passenger_data = ''
            unit_product = 'Paket'
            if vals['provider_type_name'] == 'Hotel':
                product_name = 'Hotel'
                unit_product = 'Night'
            elif vals['provider_type_name'] in ['Airline', 'Train', 'Bus']:
                product_name = 'Tiket Perjalanan'
            elif vals['provider_type_name'] in ['PPOB']:
                product_name = 'PPOB'
            elif vals['provider_type_name'] in ['Tour']:
                product_name = 'Tour'
            elif vals['provider_type_name'] == 'Activity':
                product_name = 'Jasa Lainnya'
            elif vals['provider_type_name'] == 'Visa':
                product_name = 'VISA'
            elif vals['provider_type_name'] == 'Passport':
                product_name = 'Paspor'
            product = self.get_product(data_login, product_name, unit_product)
            transaction_lines_attributes_lines = []
            if len(list_desc) > 0:
                desc = ''
                for list_desc_data in list_desc:
                    transaction_lines_attributes_lines.append({
                        "quantity": list_desc_data['quantity'],
                        "rate": list_desc_data['price'],
                        "discount": 0,
                        "product_name": product,
                        "description": list_desc_data['desc']
                    })
                    if desc:
                        desc += '; '
                    desc += list_desc_data['desc']
            else:
                price = 0
                if is_user_ho:
                    price = vals['total'] - vals['total_discount']
                else:
                    price = vals['total_nta'] - vals['total_discount'] + vals['ho_commission']
                transaction_lines_attributes_lines.append({
                    "quantity": 1,
                    "rate": price,
                    "discount": 0,
                    "product_name": product,
                    "description": desc
                })
            due_date = (datetime.strptime(vals['issued_date'].split(' ')[0],'%Y-%m-%d') + timedelta(days=vals['billing_due_date'])).strftime('%Y-%m-%d')
            issued_date = vals['issued_date'].split(' ')[0]
            data = {
                "sales_invoice": {
                    "transaction_date": issued_date,
                    "transaction_lines_attributes": transaction_lines_attributes_lines,
                    "shipping_date": issued_date,
                    "shipping_price": 0,
                    "shipping_address": "",
                    "is_shipped": False,
                    "ship_via": "",
                    "reference_no": vals['order_number'],
                    "tracking_no": "",
                    "address": "",
                    "term_name": 'Cash' if vals['billing_due_date'] == 0 else "Billing cycle %s days" % vals['billing_due_date'],
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
                    "message": '',
                    "memo": desc,
                    "custom_id": "",
                    "source": "API",
                    "use_tax_inclusive": False,
                    "tax_after_discount": False,
                    "status": "approved"
                }
            }
            _logger.info('######REQUEST SALES#########\n%s' % json.dumps(data))
            response = requests.post(url, headers=headers, json=data)
            _logger.info('######RESPONSE SALES#########\n%s' % response.text)
            if not json.loads(response.text).get('sales_invoice'):
                _logger.error('######ERROR ADD SALES JURNAL ID %s#########\n' % vals['order_number'])
                raise Exception(500, 'Error add sales')
        else:
            _logger.info('###JurnalID, Already sent to vendor accounting####')
        return 0

    def get_account(self, data_login, account_name):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }

        data = {}
        url = '%s/partner/core/api/v1/accounts' % (data_login['url_api'])
        _logger.info('######REQUEST SEARCH ACCOUNT#########\n%s' % json.dumps(data))
        res = requests.get(url, headers=headers, json=data)
        _logger.info('######RESPONSE SEARCH ACCOUNT#########\n%s' % res.text)
        res_response = json.loads(res.text)
        account_name_data = [d['name'] for d in res_response['accounts'] if d['name'] in account_name]
        if len(account_name_data) > 0:
            account_name = account_name_data[0]
        else:
            account_name = self.add_account(data_login, account_name)
        return account_name

    def add_account(self, data_login, account):
        url = "%s/partner/core/api/v1/accounts" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }
        data = {
            "account": {
                "name": account,
                "description": "Account Description %s" % account,
                "category_name": "Cash & Bank",
                "parent_category_name": "Bank Account",
                "as_a_parent": True,
                "children_names": [

                ]
            }
        }
        _logger.info('######REQUEST ADD ACCOUNT#########\n%s' % json.dumps(data))
        response = requests.post(url, headers=headers, json=data)
        _logger.info('######RESPONSE ADD ACCOUNT#########\n%s' % response.text)
        return account

    def create_journal(self, data_login, vals, account_ho, account_agent, description, date, total, tag_name):
        if len(vals['ledgers']) > 0:
            url = "%s/partner/core/api/v1/journal_entries" % data_login['url_api']
            headers = {
                "Content-Type": "application/json",
                "Authorization": "bearer %s" % data_login['access_token'],
                "api_key": data_login['api_key']
            }
            data_date = date.split(' ')[0].split('-')
            data_date.reverse()
            data = {
                "journal_entry": {
                    "transaction_date": "-".join(data_date),
                    "memo": description,
                    "transaction_account_lines_attributes": [
                      {
                        "account_name": account_agent,
                        "debit": total,
                        "description": description
                      },
                      {
                        "account_name": account_ho,
                        "credit": total,
                        "description": description
                      }
                    ],
                    "tags": [
                        tag_name
                    ]
                }
            }
            _logger.info('######REQUEST ADD LEDGER #########\n%s' % json.dumps(data))
            response = requests.post(url, headers=headers, json=data)
            _logger.info('######RESPONSE ADD LEDGER #########\n%s' % response.text)
        else:
            _logger.info('###JurnalID, Already sent to vendor accounting####')
        return 0

    def search_purchase(self, reservation_name, data_login):
        url = "%s/partner/core/api/v1/purchase_invoices" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }

        index_page = 1
        page_size = 10000
        reservation = []
        while True:
            data = {
                "page": index_page,
                "page_size": page_size,
                "sort_key": {},
                "sort_order": ""
            }
            _logger.info('######REQUEST SEARCH PURCHASE#########\n%s' % json.dumps(data))
            res = requests.get(url, headers=headers, json=data)
            _logger.info('######RESPONSE SEARCH PURCHASE#########\n%s' % json.dumps(res.text))
            res_response = json.loads(res.text)
            reservation = [d for d in res_response['purchase_invoices'] if reservation_name in d['reference_no']]
            if res_response['total_pages'] <= index_page or len(reservation) > 0:
                if len(reservation) > 0:
                    reservation = reservation[0]
                else:
                    reservation = []
                    # reservation = res_response['purchase_invoices'][0] ## FOR TESTING ONLY
                break
            index_page += 1
        return reservation

    def search_sales(self, reservation_name, data_login):
        url = "%s/partner/core/api/v1/sales_invoices" % data_login['url_api']
        headers = {
            "Content-Type": "application/json",
            "Authorization": "bearer %s" % data_login['access_token'],
            "api_key": data_login['api_key']
        }

        index_page = 1
        page_size = 10000
        reservation = []
        while True:
            data = {
                "page": index_page,
                "page_size": page_size,
                "sort_key": {},
                "sort_order": ""
            }
            _logger.info('######REQUEST SEARCH SALES#########\n%s' % json.dumps(data))
            res = requests.get(url, headers=headers, json=data)
            _logger.info('######RESPONSE SEARCH SALES#########\n%s' % json.dumps(res.text))
            res_response = json.loads(res.text)
            reservation = [d for d in res_response['sales_invoices'] if reservation_name in d['reference_no']]
            if res_response['total_pages'] <= index_page or len(reservation) > 0:
                if len(reservation) > 0:
                    reservation = reservation[0]
                else:
                    reservation = []
                    # reservation = res_response['sales_invoices'][0] ## FOR TESTING ONLY
                break
            index_page += 1
        return reservation

    def add_purchase_after_sales(self, data_login, vals):
        if len(vals['ledgers']) > 0:
            url = "%s/partner/core/api/v1/purchase_invoices" % data_login['url_api']
            headers = {
                "Content-Type": "application/json",
                "Authorization": "bearer %s" % data_login['access_token'],
                "api_key": data_login['api_key']
            }

            invoice = ''
            for rec in vals['invoice_data']:
                if invoice != '':
                    invoice += ', '
                invoice += rec
            pnr_list = {}
            for idx, segment in enumerate(vals['new_segment'], start=1):
                if not pnr_list.get(segment['pnr']):
                    pnr_list[segment['pnr']] = []
                pnr_list[segment['pnr']].append(segment)
            if pnr_list:
                ## RESCHEDULE
                for pnr in pnr_list:
                    passenger_data = ''
                    desc = ''
                    vendor_data = ''
                    for pax in vals['passengers']:
                        if passenger_data != '':
                            passenger_data += ', '
                        passenger_data += pax['name']
                    for segment in pnr_list[pnr]:
                        desc += "%s; Reschedule Tiket Perjalanan %s-%s; %s; Atas Nama: %s" % (pnr, segment['origin'], segment['destination'],segment['departure_date'].split(' ')[0], passenger_data)
                        vendor_data = segment['provider']

                    ##### AMBIL VENDOR ###############
                    vendor = self.get_vendor(data_login, vendor_data)
                    ###################################

                    ##### AMBIL PRODUCT ###############
                    # product_name = 'Reschedule Tiket Perjalanan'
                    product_name = 'Tiket Perjalanan'
                    price = vals['reschedule_amount']
                    product = self.get_product(data_login, product_name)
                    issued_date = vals['create_date'].split(' ')[0]
                    tag_name = self.search_tags(data_login, 'Rechedule Tiket')
                    self.add_purchase_after_sales_to_vendor(vals, data_login, price, product, desc, vendor, invoice, issued_date, url, headers, tag_name)
            else:
                ## ADDONS
                for reschedule_line in vals['reschedule_lines']:
                    passenger_data = ''
                    desc = ''
                    vendor_data = ''
                    for pax in vals['passengers']:
                        if passenger_data != '':
                            passenger_data += ', '
                        passenger_data += pax['name']
                    desc += "%s; Addons Tiket Perjalanan; Atas Nama: %s" % (vals['referenced_pnr'], passenger_data)
                    for provider_bookings in vals['provider_bookings']:
                        if vals['referenced_pnr'] == provider_bookings['pnr']:
                            vendor_data = provider_bookings['provider']

                    ##### AMBIL VENDOR ###############
                    vendor = self.get_vendor(data_login, vendor_data)
                    ###################################

                    ##### AMBIL PRODUCT ###############
                    # product_name = 'Addons Tiket Perjalanan'
                    product_name = 'Tiket Perjalanan'
                    price = vals['reschedule_amount']
                    product = self.get_product(data_login, product_name)
                    issued_date = vals['create_date'].split(' ')[0]
                    tag_name = self.search_tags(data_login, 'Addons (After sales)')
                    self.add_purchase_after_sales_to_vendor(vals, data_login, price, product, desc, vendor, invoice, issued_date, url, headers, tag_name)
        else:
            _logger.info('###JurnalID, Already sent to vendor accounting####')
        return 0

    def add_purchase_after_sales_to_vendor(self, vals, data_login, price, product, desc, vendor, invoice, issued_date, url, headers, tag_name):
        is_reservation_found = False
        if len(vals['reservation_name']) > 0:
            reservation_name = ''
            reservation_invoice = ''
            for rec in vals['reservation_invoice_data']:
                if reservation_invoice != '':
                    reservation_invoice = ', '
                reservation_invoice += rec
            booking_reservation_list = self.search_purchase(reservation_invoice, data_login)
            if len(booking_reservation_list) > 0:
                is_reservation_found = True
                issued_date = booking_reservation_list['transaction_date'].split('/')
                issued_date.reverse()
                issued_date = "-".join(issued_date)
                transaction_line_list = []
                tag_list = []
                if type(booking_reservation_list['tags']) is dict:
                    for rec in booking_reservation_list['tags']:
                        tag_list.append(rec['name'])
                tag_list.append(tag_name)
                for rec in booking_reservation_list['transaction_lines_attributes']:
                    transaction_line_list.append({
                        "quantity": rec['quantity'],
                        "rate": float(rec['rate']),
                        "discount": 0,
                        "product_name": rec['product']['name'],
                        "description": rec['description']
                    })
                transaction_line_list.append({
                    "quantity": 1,
                    "rate": price,
                    "discount": 0,
                    "product_name": product,
                    "description": desc
                })
                data = {
                    "purchase_invoice": {
                        "transaction_date": issued_date,
                        "transaction_lines_attributes": transaction_line_list,
                        "shipping_date": issued_date,
                        "shipping_price": 0,
                        "shipping_address": "",
                        "is_shipped": True,
                        "ship_via": "",
                        "reference_no": "%s; %s - %s" % (booking_reservation_list['reference_no'], invoice, product),
                        "tracking_no": "",
                        "address": "",
                        "term_name": "Cash",
                        "due_date": issued_date,
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
                        "tags": tag_list,
                        "email": "",
                        "message": "",
                        "memo": "%s; %s" % (booking_reservation_list['memo'], desc),
                        "custom_id": "",
                        "source": "API",
                        "use_tax_inclusive": False,
                        "tax_after_discount": False
                    }
                }
                url += '/%s' % booking_reservation_list['id']
                _logger.info('######REQUEST PURCHASE RESCHEDULE UPDATE SALES#########\n%s' % json.dumps(data))
                response = requests.patch(url, headers=headers, json=data)
                _logger.info('######RESPONSE PURCHASE RESCHEDULE UPDATE SALES#########\n%s' % response.text)
        if not is_reservation_found:
            data = {
                "purchase_invoice": {
                    "transaction_date": issued_date,
                    "transaction_lines_attributes": [
                        {
                            "quantity": 1,
                            "rate": price,
                            "discount": 0,
                            "product_name": product,
                            "description": desc
                        }
                    ],
                    "shipping_date": issued_date,
                    "shipping_price": 0,
                    "shipping_address": "",
                    "is_shipped": True,
                    "ship_via": "",
                    "reference_no": "%s - %s" % (invoice, product),
                    "tracking_no": "",
                    "address": "",
                    "term_name": "Cash",
                    "due_date": issued_date,
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
                    "tags": [
                        tag_name
                    ],
                    "email": "",
                    "message": '',
                    "memo": desc,
                    "custom_id": "",
                    "source": "API",
                    "use_tax_inclusive": False,
                    "tax_after_discount": False,
                    "status": "approved"
                }
            }
            _logger.info('######REQUEST PURCHASE RESCHEDULE#########\n%s' % json.dumps(data))
            response = requests.post(url, headers=headers, json=data)
            _logger.info('######RESPONSE PURCHASE RESCHEDULE#########\n%s' % response.text)

    def add_sales_after_sales(self, data_login, vals, contact):
        if len(vals['ledgers']) > 0:
            url = "%s/partner/core/api/v1/sales_invoices" % data_login['url_api']
            headers = {
                "Content-Type": "application/json",
                "Authorization": "bearer %s" % data_login['access_token'],
                "api_key": data_login['api_key']
            }
            passenger_data = ''
            desc = ''
            product = ''
            tag_name = ''
            for pax in vals['passengers']:
                if passenger_data != '':
                    passenger_data += ', '
                passenger_data += pax['name']
            for segment in vals['new_segment']:
                pnr = segment['pnr']
                if desc != '':
                    desc += '; '
                desc += "%s; Reschedule Tiket Perjalanan %s-%s; %s; Atas Nama: %s" % (
                pnr, segment['origin'], segment['destination'],
                segment['departure_date'].split(' ')[0], passenger_data)
                passenger_data = ''

            if desc != '':
                tag_name = self.search_tags(data_login, 'Reschedule Tiket')
                product = self.get_product(data_login, 'Tiket Perjalanan')

            for reschedule_line in vals['reschedule_lines']:
                for provider_booking in vals['provider_bookings']:
                    if provider_booking['pnr'] == vals['referenced_pnr']:
                        if desc != '':
                            desc += '; '
                        desc += "%s; Addons Tiket Perjalanan; Atas Nama: %s" % (provider_booking['pnr'], passenger_data)
                        passenger_data = ''
            if product == '':
                tag_name = self.search_tags(data_login, 'Addons (After Sales)')
                # product = self.get_product(data_login, 'Addons Tiket Perjalanan')
                product = self.get_product(data_login, 'Tiket Perjalanan')

            due_date = (datetime.strptime(vals['create_date'].split(' ')[0],'%Y-%m-%d') + timedelta(days=vals['billing_due_date'])).strftime('%d-%m-%Y')
            issued_date = vals['create_date'].split(' ')[0]
            is_reservation_found = False
            if vals['reservation_name']:
                reservation_name = vals['reservation_name']
                booking_reservation_list = self.search_sales(reservation_name, data_login)
                if len(booking_reservation_list) > 0:
                    is_reservation_found = True
                    issued_date = booking_reservation_list['transaction_date'].split('/')
                    issued_date.reverse()
                    issued_date = "-".join(issued_date)
                    due_date = booking_reservation_list['due_date'].split('/')
                    due_date.reverse()
                    due_date = "-".join(due_date)
                    transaction_line_list = []
                    tag_list = []
                    if type(booking_reservation_list['tags']) is dict:
                        for rec in booking_reservation_list['tags']:
                            tag_list.append(rec['name'])
                    tag_list.append(tag_name)
                    for rec in booking_reservation_list['transaction_lines_attributes']:
                        transaction_line_list.append({
                            "quantity": rec['quantity'],
                            "rate": rec['amount'],
                            "discount": 0,
                            "product_name": rec['product']['name'],
                            "description": rec['description']
                        })
                    transaction_line_list.append({
                        "quantity": 1,
                        "rate": vals['total_amount'],
                        "discount": 0,
                        "product_name": product,
                        "description": desc
                    })
                    data = {
                        "sales_invoice": {
                            "transaction_date": issued_date,
                            "transaction_lines_attributes": transaction_line_list,
                            "shipping_date": issued_date,
                            "shipping_price": 0,
                            "shipping_address": "",
                            "is_shipped": False,
                            "ship_via": "",
                            "reference_no": booking_reservation_list['reference_no'],
                            "tracking_no": "",
                            "address": "",
                            "term_name": 'Cash' if vals['billing_due_date'] == 0 else "Billing cycle %s days" % vals['billing_due_date'],
                            "due_date": due_date,
                            "deposit": 0,
                            "discount_unit": 0,
                            "witholding_value": 0,
                            "witholding_type": "percent",
                            "discount_type_name": "percent",
                            "person_name": contact,
                            "warehouse_name": "",
                            "warehouse_code": "",
                            "tags": tag_list,
                            "email": vals['booker'].get('email', ''),
                            "message": "",
                            "memo": "%s; %s" % (booking_reservation_list['memo'], desc),
                            "custom_id": "",
                            "source": "API",
                            "use_tax_inclusive": False,
                            "tax_after_discount": False
                        }
                    }
                    url += '/%s' % booking_reservation_list['id']
                    _logger.info('######REQUEST PURCHASE RESCHEDULE UPDATE SALES#########\n%s' % json.dumps(data))
                    response = requests.patch(url, headers=headers, json=data)
                    _logger.info('######RESPONSE PURCHASE RESCHEDULE UPDATE SALES#########\n%s' % response.text)
            if not is_reservation_found:
                data = {
                    "sales_invoice": {
                        "transaction_date": issued_date,
                        "transaction_lines_attributes": [
                            {
                                "quantity": 1,
                                "rate": vals['total_amount'],
                                "discount": 0,
                                "product_name": product,
                                "description": desc
                            }
                        ],
                        "shipping_date": issued_date,
                        "shipping_price": 0,
                        "shipping_address": "",
                        "is_shipped": False,
                        "ship_via": "",
                        "reference_no": vals['order_number'],
                        "tracking_no": "",
                        "address": "",
                        "term_name": 'Cash' if vals['billing_due_date'] == 0 else "Billing cycle %s days" % vals['billing_due_date'],
                        "due_date": due_date,
                        "deposit": 0,
                        "discount_unit": 0,
                        "witholding_value": 0,
                        "witholding_type": "percent",
                        "discount_type_name": "percent",
                        "person_name": contact,
                        "warehouse_name": "",
                        "warehouse_code": "",
                        "tags": [
                            tag_name
                        ],
                        "email": vals['booker'].get('email', ''),
                        "message": '',
                        "memo": desc,
                        "custom_id": "",
                        "source": "API",
                        "use_tax_inclusive": False,
                        "tax_after_discount": False,
                        "status": "approved"
                    }
                }
                _logger.info('######REQUEST SALES RESCHEDULE UPDATE SALES#########\n%s' % json.dumps(data))
                response = requests.post(url, headers=headers, json=data)
                _logger.info('######RESPONSE SALES RESCHEDULE UPDATE SALES#########\n%s' % response.text)
        else:
            _logger.info('###JurnalID, Already sent to vendor accounting####')
        return 0

    def add_sales_order(self, vals):
        try:
            cookies = False
            data_login = self.acc_login(vals)

            if vals['category'] == 'reservation':
                ##### AMBIL CONTACT ###############
                contact = self.get_contact(data_login, vals)
                ###################################
                ####### CREATE PURCHASE INVOICE ##########
                self.add_purchase(data_login, vals)
                ###################################

                ####### CREATE SALES INVOICE ##########
                self.add_sales(data_login, vals, contact)
                ###################################
            elif vals['category'] == 'top_up':
                ######## GET ACCOUNT ############
                if len(vals['ledgers']) > 0:
                    account_ho = self.get_account(data_login, vals['bank'])
                    account_agent = self.get_account(data_login, "Deposit System %s" % vals['agent_name'])
                    tag_name = self.search_tags(data_login, 'Top Up')
                    self.create_journal(data_login, vals, account_ho, account_agent, "TOP UP %s %s" % (account_agent, vals['name']),vals['date'], vals['total'], tag_name)
                else:
                    _logger.info('###JurnalID, Already sent to vendor accounting####')
            elif vals['category'] == 'reschedule':
                ## HANYA UNTUK AIRLINE
                ##### AMBIL CONTACT ###############
                contact = self.get_contact(data_login, vals)
                ###################################

                ####### CREATE PURCHASE INVOICE ##########
                self.add_purchase_after_sales(data_login, vals)
                ###################################

                ####### CREATE SALES INVOICE ##########
                self.add_sales_after_sales(data_login, vals, contact)
                ###################################
                pass
            elif vals['category'] == 'refund':
                ## HANYA UNTUK AIRLINE
                ####### REFUND ################
                ##### VENDOR TO HEAD OFFICE #######
                if len(vals['ledgers']) > 0:
                    desc = ''
                    passenger_data = ''
                    vendor_name = ''

                    for pax in vals['refund_lines']:
                        if passenger_data != '':
                            passenger_data += ', '
                        passenger_data += pax['name']
                    for segment in vals['new_segment']:
                        pnr = segment['pnr']
                        if desc != '':
                            desc += '; '
                        desc += "%s; Reschedule Tiket Perjalanan %s-%s; %s; Atas Nama: %s" % (
                        pnr, segment['origin'], segment['destination'],
                        segment['departure_date'].split(' ')[0], passenger_data)
                        passenger_data = ''


                    for provider_booking in vals['provider_bookings']:
                        if provider_booking['pnr'] == vals['referenced_pnr']:
                            vendor_name = provider_booking['provider']
                            pnr = provider_booking['pnr']
                            if desc != '':
                                desc += '; '
                            desc += "%s; REFUND Tiket Perjalanan %s-%s; %s; Atas Nama: %s" % (
                                pnr, provider_booking['origin'], provider_booking['destination'],
                                provider_booking['departure_date'].split(' ')[0], passenger_data)
                            passenger_data = ''
                            break

                    ####### REFUND #################

                    ##### VENDOR TO HEAD OFFICE #######
                    account_vendor = self.get_account(data_login, vendor_name)
                    account_ho = self.get_account(data_login, "Cash")
                    tag_name = self.search_tags(data_login, 'Refund Tiket')
                    self.create_journal(data_login, vals, account_vendor, account_ho, desc, vals['real_refund_date'], vals['refund_amount'], tag_name)


                    ##### HEAD OFFICE TO AGENT ########
                    account_customer = self.get_account(data_login, "Deposit System %s" % vals['agent_name'])
                    tag_name = self.search_tags(data_login, 'Refund Tiket')
                    self.create_journal(data_login, vals, account_ho, account_customer, desc, vals['refund_date'], vals['total_amount'], tag_name)

                else:
                    _logger.info('###JurnalID, Already sent to vendor accounting####')
            res = self.response_parser_success()
        except Exception as e:
            _logger.error("%s, %s" % (str(e), traceback.format_exc()))
            res = self.response_parser_error()
        return res

    def response_parser_success(self):
        res = {
            'status': 'success',
            'content': ''
        }
        return res

    def response_parser_error(self):
        res = {
            'status': 'error',
            'content': ''
        }
        return res
