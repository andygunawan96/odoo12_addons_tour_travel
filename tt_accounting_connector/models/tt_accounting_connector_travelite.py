from odoo import api, fields, models, _
import logging
import requests
import json
import base64
import time
from datetime import datetime
from random import randrange

_logger = logging.getLogger(__name__)


class AccountingConnectorTravelite(models.Model):
    _name = 'tt.accounting.connector.travelite'
    _description = 'Accounting Connector Travelite'

    def check_credit_limit(self, vals):
        if not vals.get('customer_id'):
            raise Exception('Request cannot be sent because some field requirements are not met. Missing: "customer_id"')
        if not vals.get('ho_id'):
            raise Exception('Request cannot be sent because some field requirements are not met. Missing: "ho_id"')
        url_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'customer_url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "customer_url" in Travelite / TOP Accounting Setup!')
        username_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'username')], limit=1)
        if not username_obj:
            raise Exception('Please provide a variable with the name "username" in Travelite / TOP Accounting Setup!')
        password_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'password')], limit=1)
        if not password_obj:
            raise Exception('Please provide a variable with the name "password" in Travelite / TOP Accounting Setup!')
        include_book_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'credit_limit_include_booking')], limit=1)
        include_dp_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'credit_limit_include_dp')], limit=1)

        is_include_book = include_book_obj and include_book_obj.variable_value or "1"
        is_include_dp = include_dp_obj and include_dp_obj.variable_value or "0"
        url = '%s/checkcreditlimit?&custid=%s&includeBooking=%s&includeDP=%s' % (url_obj.variable_value, vals['customer_id'], is_include_book, is_include_dp)
        username = username_obj.variable_value
        password = password_obj.variable_value
        headers = {
            'username': username,
            'password': password
        }
        _logger.info('Travelite / TOP Request Check Credit Limit: %s', str(vals['customer_id']))
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception('Error %s' % str(response.status_code))
        temp_res = response.content and response.content.decode("UTF-8") or ''
        temp_split = temp_res.split(';')
        res = len(temp_split) > 1 and temp_split[1] or temp_split[0]
        return float(res)

    def add_customer(self, vals):
        if not vals.get('ho_id'):
            raise Exception('Request cannot be sent because some field requirements are not met. Missing: "ho_id"')
        url_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'customer_url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "customer_url" in Travelite / TOP Accounting Setup!')
        username_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'username')], limit=1)
        if not username_obj:
            raise Exception('Please provide a variable with the name "username" in Travelite / TOP Accounting Setup!')
        password_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'password')], limit=1)
        if not password_obj:
            raise Exception('Please provide a variable with the name "password" in Travelite / TOP Accounting Setup!')

        url = '%s/create' % url_obj.variable_value
        username = username_obj.variable_value
        password = password_obj.variable_value
        headers = {
            'Content-Type': 'application/json',
            'username': username,
            'password': password
        }
        req_data = self.request_parser_customer(vals)
        _logger.info('Travelite / TOP Request Add Customer: %s', req_data)
        if vals.get('accounting_queue_id'):
            queue_obj = self.env['tt.accounting.queue'].browse(int(vals['accounting_queue_id']))
            if queue_obj:
                queue_obj.write({
                    'request': req_data
                })
        response = requests.post(url, data=req_data, headers=headers)
        res = self.response_parser_customer(response)

        if res['status'] == 'success':
            _logger.info('Travelite / TOP Insert Customer Success')
            cust_parent_obj = self.env['tt.customer.parent'].search([('seq_id', '=', vals['seq_id'])], limit=1)
            if cust_parent_obj:
                cust_parent_obj[0].write({
                    'accounting_uid': str(res['content'])
                })
        else:
            _logger.info('Travelite / TOP Insert Customer Failed')
        _logger.info(res)
        return res

    def request_parser_customer(self, request):
        address_list = []
        first_post_code = ''
        first_country = ''
        first_city = ''
        if not request.get('address_list'):
            address_list.append({
                'address': '-'
            })
        for rec in request['address_list']:
            if rec.get('address'):
                address_list.append({
                    'address': rec['address']
                })
                if not first_post_code:
                    first_post_code = rec.get('zip') and rec['zip'] or ''
                if not first_country:
                    first_country = rec.get('country') and rec['country'] or ''
                if not first_city:
                    first_city = rec.get('city') and rec['city'] or ''
        ctp_list = []
        if not request.get('booker_list'):
            ctp_list.append({
                'maincctcname': '-'
            })
        for rec in request['booker_list']:
            if rec.get('name'):
                ctp_list.append({
                    'maincctcname': rec['name']
                })
        phone_list = []
        for rec in request['phone_list']:
            if rec.get('calling_number'):
                phone_list.append('%s%s' % (rec.get('calling_code', '62'), rec['calling_number']))
        def_cust_email = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'),
             ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('accounting_setup_id.active', '=', True),
             ('variable_name', '=', 'default_cust_email')], limit=1)
        cust_email = def_cust_email and def_cust_email.variable_value or 'orbis@company.com'
        req = {
            "custcode": '', # bisa di isi seq_id, tapi kosongkan saja supaya generate otomatis dari TOP
            "custname": request.get('customer_parent_name') and request['customer_parent_name'] or '',
            "custpostcode": first_post_code,
            "cgroup": 'C',
            "custtype": request.get('customer_parent_type_code') == 'cor' and '5' or '1',
            "ppnflag": False,
            "mobileno": len(phone_list) > 0 and phone_list[0] or '000000000000',
            "custphone1": len(phone_list) > 1 and phone_list[1] or '000000000000',
            "custphone2": len(phone_list) > 2 and phone_list[2] or '000000000000',
            "custfax1": '000000000000',
            "custaddress1": address_list and address_list[0]['address'] or '-',
            "custemail": request.get('email') and request['email'] or cust_email,
            "businessregdate": datetime.now().strftime('%Y-%m-%d'),
            "citydesc": first_city and first_city or 'Jakarta',
            "countrydesc": first_country and first_country or 'Indonesia',
            "showgst": 0,
            "showfee": 0,
            "idtype": "0",
            "tmrflag": False,
            "contactperson": ctp_list,
            "billingaddress": address_list
        }
        return json.dumps(req)

    def response_parser_customer(self, response):
        res = {
            'status_code': response.status_code or 500,
            'content': response.content or ''
        }
        if res['status_code'] == 200:
            status = 'success'
        else:
            status = 'failed'
        if res.get('content'):
            try:
                res.update({
                    'content': res['content'].decode("UTF-8")
                })
            except (UnicodeDecodeError, AttributeError):
                pass
        else:
            res['content'] = ''
        res.update({
            'status': status
        })
        return res

    def add_sales_order(self, vals):
        url_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in Travelite / TOP Accounting Setup!')
        username_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'username')], limit=1)
        if not username_obj:
            raise Exception('Please provide a variable with the name "username" in Travelite / TOP Accounting Setup!')
        password_obj = self.env['tt.accounting.setup.variables'].search(
            [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
             ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'password')], limit=1)
        if not password_obj:
            raise Exception('Please provide a variable with the name "password" in Travelite / TOP Accounting Setup!')

        url = url_obj.variable_value
        username = username_obj.variable_value
        password = password_obj.variable_value
        headers = {
            'Content-Type': 'application/json',
            'username': username,
            'password': password
        }
        req_data = self.request_parser(vals)
        _logger.info('Travelite / TOP Request Add Sales Order: %s', req_data)
        if vals.get('accounting_queue_id'):
            queue_obj = self.env['tt.accounting.queue'].browse(int(vals['accounting_queue_id']))
            if queue_obj:
                queue_obj.write({
                    'request': req_data
                })
        # res = util.send_request_json(self._get_web_hook('Sales%20Order'), post=vals, headers=headers)
        response = requests.post(url, data=req_data, headers=headers)
        res = self.response_parser(response)

        if res['status'] == 'success':
            _logger.info('Travelite / TOP Insert Success')
        else:
            _logger.info('Travelite / TOP Insert Failed')
        _logger.info(res)

        return res

    def request_parser(self, request):
        is_ho_transaction = False
        if request.get('agent_id'):
            agent_obj = self.env['tt.agent'].browse(int(request['agent_id']))
            if agent_obj and agent_obj.is_ho_agent:
                is_ho_transaction = True
        if request['category'] == 'reservation':
            source_type_id_obj = self.env['tt.accounting.setup.variables'].search(
                [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
                 ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', 'sourcetypeid')], limit=1)
            if not source_type_id_obj:
                raise Exception('Please provide a variable with the name "sourcetypeid" in Travelite / TOP Accounting Setup!')
            is_create_inv_obj = self.env['tt.accounting.setup.variables'].search(
                [('accounting_setup_id.accounting_provider', '=', 'travelite'), ('accounting_setup_id.active', '=', True),
                 ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', 'is_create_invoice')], limit=1)
            vat_var_obj = self.env['tt.accounting.setup.variables'].search(
                [('accounting_setup_id.accounting_provider', '=', 'travelite'),
                 ('accounting_setup_id.active', '=', True),
                 ('accounting_setup_id.ho_id', '=', int(request['ho_id'])),
                 ('variable_name', '=', '%s_vat_var' % request['provider_type'])], limit=1)
            vat_perc_obj = self.env['tt.accounting.setup.variables'].search(
                [('accounting_setup_id.accounting_provider', '=', 'travelite'),
                 ('accounting_setup_id.active', '=', True),
                 ('accounting_setup_id.ho_id', '=', int(request['ho_id'])),
                 ('variable_name', '=', '%s_vat_percentage' % request['provider_type'])], limit=1)
            always_use_contactcd = self.env['tt.accounting.setup.variables'].search(
                [('accounting_setup_id.accounting_provider', '=', 'travelite'),
                 ('accounting_setup_id.active', '=', True),
                 ('accounting_setup_id.ho_id', '=', int(request['ho_id'])),
                 ('variable_name', '=', 'always_use_contactcd')], limit=1)

            source_type_id = source_type_id_obj.variable_value
            is_create_inv = is_create_inv_obj and is_create_inv_obj.variable_value or False
            customer_id = 0
            customer_seq_id = ""
            customer_name = ""
            if request.get('customer_parent_id'):
                customer_obj = self.env['tt.customer.parent'].browse(int(request['customer_parent_id']))
                if customer_obj.accounting_uid:
                    if always_use_contactcd and always_use_contactcd.variable_value:
                        customer_seq_id = customer_obj.accounting_uid
                    else:
                        customer_id = customer_obj.accounting_uid
                        if customer_id.isdigit():
                            customer_id = int(customer_id)
                elif customer_obj.seq_id:
                    customer_seq_id = customer_obj.seq_id

                if customer_obj.name:
                    customer_name = customer_obj.name
            ticket_itin_list = []
            ticket_itin_idx = 0
            ticket_list = []
            req = {
                "booking": {
                    "custid": customer_id,
                    "custcode": customer_seq_id,
                    "custname": customer_name,
                    "cctcname": "%s %s" % (request['contact']['title'], request['contact']['name']),
                    "cctcphone": request['contact']['phone'],
                    "cctcaddress": "-",
                    "email": request['contact']['email'],
                    "ref_invoice": "",
                    "ref_bookcode": request['order_number'],
                    "bookingext": request['order_number'],
                    "invoiceflag": is_create_inv,
                    "sourcetypeid": source_type_id,
                    "printflag": False,
                    "autopaidbydp": False,
                    "userid": request.get('issued_accounting_uid') and request['issued_accounting_uid'] or ''
                }
            }
            for prov in request['provider_bookings']:
                if request['provider_type'] == 'airline':
                    pax_segment_list = []
                    pax_segment_classes = []
                    first_carrier_code = ''
                    for journ in prov['journeys']:
                        for segm in journ['segments']:
                            ticket_itin_list.append({
                                "segmentid": ticket_itin_idx + 1,
                                "departdate": segm['departure_date'].split(' ')[0],
                                "departtime": segm['departure_date'].split(' ')[1][:5],
                                "departapt": segm['origin'],
                                "arriveddate": segm['arrival_date'].split(' ')[0],
                                "arrivedtime": segm['arrival_date'].split(' ')[1][:5],
                                "arrivedapt": segm['destination'],
                                "originalpnr": prov['pnr'],
                                "pnrcode": prov['pnr'],
                                "airlinecode": segm['carrier_code'],
                                "flightclass": segm['cabin_class'],
                                "flightno": segm['carrier_number'],
                                "proddtlcode": request.get('sector_type') == 'Domestic' and 'TKTD' or 'TKTI',
                                "stopover": 0,
                                "status": segm['status']
                            })
                            pax_segment_list.append({
                                "segmentid": ticket_itin_idx + 1
                            })
                            if not segm['cabin_class'] in pax_segment_classes:
                                pax_segment_classes.append(segm['cabin_class'])
                            if not first_carrier_code:
                                first_carrier_code = segm['carrier_code']
                            ticket_itin_idx += 1
                    for pax_idx, pax in enumerate(prov['tickets']):
                        if pax.get('ticket_number'):
                            if '-' not in pax['ticket_number']:
                                if len(pax['ticket_number']) >= 13:
                                    pax_tick = pax['ticket_number'][3:]
                                    airline_id = pax['ticket_number'][:3]
                                else:
                                    pax_tick = pax['ticket_number']
                                    airline_id = ''
                            else:
                                tix_split = pax['ticket_number'].split('-', 1)
                                pax_tick = tix_split[1]
                                airline_id = tix_split[0]
                        else:
                            pax_tick = '%s_%s' % (prov['pnr'], str(pax_idx+1))
                            airline_id = ''
                        pax_type_conv = {
                            'ADT': 'AD',
                            'CHD': 'CH',
                            'INF': 'IN',
                        }
                        if is_ho_transaction:
                            ho_prof = pax.get('total_commission') and pax['total_commission'] or 0
                        else:
                            ho_prof = pax.get('ho_commission') and pax['ho_commission'] or 0
                            if pax.get('parent_agent_commission'):
                                ho_prof += pax['parent_agent_commission']

                        pax_setup = {
                            'ho_profit': ho_prof,
                            'agent_profit': pax.get('agent_commission') and pax['agent_commission'] or 0,
                            'total_comm': pax.get('total_commission') and pax['total_commission'] or 0,
                            'total_nta': pax.get('total_nta') and pax['total_nta'] or 0,
                            'agent_nta': pax.get('agent_nta') and pax['agent_nta'] or 0,
                            'total_fare': pax.get('total_fare') and pax['total_fare'] or 0,
                            'total_tax': pax.get('total_tax') and pax['total_tax'] or 0,
                            'total_upsell': pax.get('total_upsell') and pax['total_upsell'] or 0,
                            'total_discount': pax.get('total_discount') and pax['total_discount'] or 0,
                            'breakdown_service_fee': pax.get('breakdown_service_fee') and pax['breakdown_service_fee'] or 0,
                            'breakdown_vat': pax.get('breakdown_vat') and pax['breakdown_vat'] or 0
                        }

                        temp_sales = pax_setup['agent_nta']
                        temp_upsell = pax_setup['total_upsell'] - pax_setup['agent_profit']
                        if is_ho_transaction:
                            temp_sales += ho_prof - pax_setup['total_upsell']
                            temp_upsell += pax_setup['agent_profit']
                        if pax_setup['total_upsell'] == 0:
                            temp_upsell = 0
                        # if pax_setup['breakdown_service_fee'] > 0:
                        #     temp_sales = pax_setup['total_nta'] + pax_setup['breakdown_service_fee']
                        if pax_setup['breakdown_vat'] > 0:
                            temp_sales -= pax_setup['breakdown_vat']
                        pax_setup.update({
                            'total_sales': temp_sales
                        })

                        tax_details = {}
                        tax_details_len = 0
                        for temp_tax in pax['tax_details']:
                            tax_details.update({
                                "tax%s" % str(tax_details_len + 1): temp_tax['charge_code'],
                                "taxamt%s" % str(tax_details_len + 1): temp_tax['amount']
                            })
                            tax_details_len += 1
                        while tax_details_len < 10:
                            tax_details.update({
                                "tax%s" % str(tax_details_len + 1): None,
                                "taxamt%s" % str(tax_details_len + 1): 0.0
                            })
                            tax_details_len += 1

                        if not vat_var_obj or not vat_perc_obj:
                            _logger.info('Please set both {provider_type_code}_vat_var and {provider_type_code}_vat_percentage variables.')
                            vat = 0
                        else:
                            temp_vat_var = pax_setup.get(vat_var_obj.variable_value) and pax_setup[vat_var_obj.variable_value] or 0
                            vat = round(temp_vat_var * float(vat_perc_obj.variable_value) / 100)

                        ticket_list.append({
                            "segment": pax_segment_list,
                            "proddtlcode": request['sector_type'] == 'Domestic' and 'TKTD' or 'TKTI',
                            "pnrcode": prov['pnr'],
                            "originalpnr": prov['pnr'],
                            "issuedate": request['issued_date'].split(' ')[0],
                            "airlineid": airline_id,
                            "suppid": 0,
                            "suppname": "",
                            "ticketno": pax_tick,
                            "passtitle": pax['title'],
                            "passengername": "%s %s" % (pax['first_name'], pax['last_name']),
                            "passtype": pax_type_conv.get(pax['pax_type']) and pax_type_conv[pax['pax_type']] or 'AD',
                            "classtype": ",".join(pax_segment_classes),
                            "sourcetypeid": source_type_id,
                            "airlinecode": first_carrier_code,
                            "pubfare": pax_setup['total_fare'] + ho_prof,
                            "airporttax": pax_setup['total_tax'],
                            "commission": ho_prof,
                            "servicefee": pax_setup['breakdown_service_fee'],
                            "sellgst": 0,
                            "surcharge": 0.0000,
                            'discamt': pax_setup['total_discount'],
                            "markupamt": temp_upsell,
                            "sellpricenotax": pax_setup['total_fare'] + temp_upsell,
                            "nettfare": pax_setup['total_fare'],
                            "nettprice": pax_setup['total_nta'],
                            "sellprice": temp_sales,
                            "currid": prov['currency'],
                            "pubfareccy": prov['currency'],
                            "nettcurrid": prov['currency'],
                            "commpercent": 0.0,
                            "taxdetail": tax_details
                        })
                elif request['provider_type'] == 'train':
                    pax_segment_list = []
                    pax_segment_classes = []
                    first_carrier_name = ''
                    for journ in prov['journeys']:
                        ticket_itin_list.append({
                            "segmentid": ticket_itin_idx + 1,
                            "departdate": journ['departure_date'].split(' ')[0],
                            "departtime": journ['departure_date'].split(' ')[1][:5],
                            "departapt": journ['origin'],
                            "arriveddate": journ['arrival_date'].split(' ')[0],
                            "arrivedtime": journ['arrival_date'].split(' ')[1][:5],
                            "arrivedapt": journ['destination'],
                            "originalpnr": prov['pnr'],
                            "pnrcode": prov['pnr'],
                            "airlinecode": "KI",
                            "flightclass": journ['cabin_class'],
                            "flightno": journ['carrier_number'],
                            "proddtlcode": "TKKA",
                            "status": "OK"
                        })
                        pax_segment_list.append({
                            "segmentid": ticket_itin_idx + 1
                        })
                        if not journ['cabin_class'] in pax_segment_classes:
                            pax_segment_classes.append(journ['cabin_class'])
                        if not first_carrier_name:
                            first_carrier_name = journ['carrier_name']
                        ticket_itin_idx += 1
                    for pax_idx, pax in enumerate(prov['tickets']):
                        if pax.get('ticket_number'):
                            pax_tick = pax['ticket_number']
                        else:
                            pax_tick = '%s_%s' % (prov['pnr'], str(pax_idx+1))
                        pax_type_conv = {
                            'ADT': 'AD',
                            'CHD': 'CH',
                            'INF': 'IN',
                        }
                        if is_ho_transaction:
                            ho_prof = pax.get('total_commission') and pax['total_commission'] or 0
                        else:
                            ho_prof = pax.get('ho_commission') and pax['ho_commission'] or 0
                            if pax.get('parent_agent_commission'):
                                ho_prof += pax['parent_agent_commission']

                        pax_setup = {
                            'ho_profit': ho_prof,
                            'agent_profit': pax.get('agent_commission') and pax['agent_commission'] or 0,
                            'total_comm': pax.get('total_commission') and pax['total_commission'] or 0,
                            'total_nta': pax.get('total_nta') and pax['total_nta'] or 0,
                            'agent_nta': pax.get('agent_nta') and pax['agent_nta'] or 0,
                            'total_fare': pax.get('total_fare') and pax['total_fare'] or 0,
                            'total_upsell': pax.get('total_upsell') and pax['total_upsell'] or 0,
                            'total_discount': pax.get('total_discount') and pax['total_discount'] or 0,
                            'breakdown_service_fee': pax.get('breakdown_service_fee') and pax['breakdown_service_fee'] or 0,
                            'breakdown_vat': pax.get('breakdown_vat') and pax['breakdown_vat'] or 0
                        }

                        temp_sales = pax_setup['agent_nta']
                        temp_upsell = pax_setup['total_upsell'] - pax_setup['agent_profit']
                        if is_ho_transaction:
                            temp_sales += ho_prof - pax_setup['total_upsell']
                            temp_upsell += pax_setup['agent_profit']
                        if pax_setup['total_upsell'] == 0:
                            temp_upsell = 0
                        # if pax_setup['breakdown_service_fee'] > 0:
                        #     temp_sales = pax_setup['total_nta'] + pax_setup['breakdown_service_fee']
                        if pax_setup['breakdown_vat'] > 0:
                            temp_sales -= pax_setup['breakdown_vat']
                        pax_setup.update({
                            'total_sales': temp_sales
                        })

                        if not vat_var_obj or not vat_perc_obj:
                            _logger.info('Please set both {provider_type_code}_vat_var and {provider_type_code}_vat_percentage variables.')
                            vat = 0
                        else:
                            temp_vat_var = pax_setup.get(vat_var_obj.variable_value) and pax_setup[vat_var_obj.variable_value] or 0
                            vat = round(temp_vat_var * float(vat_perc_obj.variable_value) / 100)

                        ticket_list.append({
                            "segment": pax_segment_list,
                            "proddtlcode": "TKKA",
                            "pnrcode": prov['pnr'],
                            "originalpnr": prov['pnr'],
                            "issuedate": request['issued_date'].split(' ')[0],
                            "suppid": 0,
                            "suppname": "",
                            "ticketno": pax_tick,
                            "passtitle": pax['title'],
                            "passengername": pax['passenger'],
                            "passtype": pax_type_conv.get(pax['pax_type']) and pax_type_conv[pax['pax_type']] or 'AD',
                            "classtype": ",".join(pax_segment_classes),
                            "sourcetypeid": source_type_id,
                            "airlinecode": "KI",
                            "pubfare": pax_setup['total_fare'] + ho_prof,
                            "commission": ho_prof,
                            "servicefee": pax_setup['breakdown_service_fee'],
                            "sellgst": 0,
                            "surcharge": 0.0000,
                            'discamt': pax_setup['total_discount'],
                            "markupamt": temp_upsell,
                            "sellpricenotax": pax_setup['total_fare'] + temp_upsell,
                            "nettfare": pax_setup['total_fare'],
                            "nettprice": pax_setup['total_nta'],
                            "sellprice": temp_sales,
                            "currid": prov['currency'],
                            "pubfareccy": prov['currency'],
                            "nettcurrid": prov['currency'],
                            "convertrate": 1
                        })
                elif request['provider_type'] == 'hotel':
                    if is_ho_transaction:
                        ho_prof = prov.get('total_commission') and prov['total_commission'] or 0
                    else:
                        ho_prof = prov.get('ho_commission') and prov['ho_commission'] or 0
                        if prov.get('parent_agent_commission'):
                            ho_prof += prov['parent_agent_commission']

                    prov_setup = {
                        'ho_profit': ho_prof,
                        'agent_profit': prov.get('agent_commission') and prov['agent_commission'] or 0,
                        'total_comm': prov.get('total_commission') and prov['total_commission'] or 0,
                        'total_nta': prov.get('total_nta') and prov['total_nta'] or 0,
                        'agent_nta': prov.get('agent_nta') and prov['agent_nta'] or 0,
                        'total_fare': prov.get('total_fare') and prov['total_fare'] or 0,
                        'total_upsell': prov.get('total_upsell') and prov['total_upsell'] or 0,
                        'total_discount': prov.get('total_discount') and prov['total_discount'] or 0,
                        'breakdown_service_fee': prov.get('breakdown_service_fee') and prov['breakdown_service_fee'] or 0,
                        'breakdown_vat': prov.get('breakdown_vat') and prov['breakdown_vat'] or 0
                    }

                    temp_sales = prov_setup['agent_nta']
                    if is_ho_transaction:
                        temp_sales += ho_prof
                    # if prov_setup['breakdown_service_fee'] > 0:
                    #     temp_sales = prov_setup['total_nta'] + prov_setup['breakdown_service_fee']
                    if prov_setup['breakdown_vat'] > 0:
                        temp_sales -= prov_setup['breakdown_vat']
                    prov_setup.update({
                        'total_sales': temp_sales
                    })

                    if not vat_var_obj or not vat_perc_obj:
                        _logger.info('Please set both {provider_type_code}_vat_var and {provider_type_code}_vat_percentage variables.')
                        vat = 0
                    else:
                        temp_vat_var = prov_setup.get(vat_var_obj.variable_value) and prov_setup[vat_var_obj.variable_value] or 0
                        vat = round(temp_vat_var * float(vat_perc_obj.variable_value) / 100)

                    pax_list = []
                    for pax in prov['passengers']:
                        pax_list.append({
                            "passtitle": pax['title'],
                            "passname": pax['name'],
                            "passtype": "AD"
                        })

                    room_list = []
                    room_type_list = []
                    for room in prov['rooms']:
                        room_type = room.get('room_type') and room['room_type'] or room['room_name']
                        if room_type not in room_type_list:
                            room_type_list.append(room_type)
                        room_list.append({
                            "checkin": "%sT00:00:00" % prov['checkin_date'],
                            "checkout": "%sT00:00:00" % prov['checkout_date'],
                            "nites": int(request['nights']),
                            "nettcurrid": prov['currency'],
                            "nettprice": prov_setup['total_nta'] / len(prov['rooms']) / int(request['nights']),
                            "currid": prov['currency'],
                            "sellprice": temp_sales / len(prov['rooms']) / int(request['nights']),
                            "servicefee": prov_setup['breakdown_service_fee'] / len(prov['rooms']) / int(request['nights']),
                            "totalsell": temp_sales / len(prov['rooms']),
                            "totalnett": prov_setup['total_fare'] / len(prov['rooms'])
                        })
                    hotel_country = '-'
                    hotel_city_obj = self.env['res.city'].search([('name', 'ilike', prov['hotel_city'])], limit=1)
                    if hotel_city_obj:
                        hotel_country = hotel_city_obj.country_id and hotel_city_obj.country_id.name or '-'

                    ticket_list.append({
                        "prodcode": "HT",
                        "proddtlcode": "HTHD",
                        "pnrcode": prov['pnr'],
                        "suppid": 0,
                        "hotelcityid": 0,
                        "hotelid": 0,
                        "hotelname": prov['hotel_name'],
                        "htcountrydesc": hotel_country,
                        "hotelcitydesc": prov['hotel_city'],
                        "htphoneno": prov['hotel_phone'],
                        "roomtypedesc": room_type_list and room_type_list[0] or "-",
                        "classtypedesc": room_type_list and room_type_list[0] or "-",
                        "checkin": prov['checkin_date'],
                        "checkout": prov['checkout_date'],
                        "totnites": int(request['nights']),
                        "totroom": len(prov['rooms']),
                        "totperson": len(prov['passengers']),
                        "bfastflag": True,
                        "nettcurrid": prov['currency'],
                        "currid": prov['currency'],
                        "totnettprice": prov_setup['total_nta'],
                        "totservicefee": prov_setup['breakdown_service_fee'],
                        "totsellprice": temp_sales,
                        "canceldateline": "",
                        "confirmationno": prov['pnr'],
                        "bookdesc": "",
                        "source": "N",
                        "totsellgst": 0,
                        "status": "CONFIRMED",
                        "dealer": request['contact']['name'],
                        "bookdate": request.get('issued_date') and request['issued_date'][:10] or '',
                        "suppcode": "",
                        "suppname": "",
                        "sourcetypeid": source_type_id,
                        "autoflag": True,
                        "hotel_detail": room_list,
                        "hotel_passenger": pax_list
                    })
            if request['provider_type'] in ['airline', 'train']:
                req.update({
                    "ticket_itin": ticket_itin_list,
                    "ticket": ticket_list
                })
            elif request['provider_type'] == 'hotel':
                req.update({
                    "hotel": ticket_list
                })
        else:
            req = {}
        return json.dumps(req)

    def response_parser(self, response):
        res = {
            'status_code': response.status_code or 500,
            'content': response.content or ''
        }
        if res.get('content'):
            try:
                res.update({
                    'content': json.loads(res['content'].decode("UTF-8"))
                })
            except (UnicodeDecodeError, AttributeError):
                pass
        if res['content'].get('message') == 'SUCCESS':
            status = 'success'
        else:
            status = 'failed'
        res.update({
            'status': status,
        })
        return res
