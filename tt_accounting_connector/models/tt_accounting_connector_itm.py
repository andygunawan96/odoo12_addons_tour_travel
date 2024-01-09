from odoo import api, fields, models, _
import logging
import requests
import json
import base64
import time
from datetime import datetime
from random import randrange

_logger = logging.getLogger(__name__)
# url = 'http://cloud1.suvarna-mi.com:1293/Data15/RunTravelfileV3'
# live_id = 'b02849bd-788f-401e-a039-9afba72e3c9d'
# product_code = 'AVINTBSP'


class AccountingConnectorITM(models.Model):
    _name = 'tt.accounting.connector.itm'
    _description = 'Accounting Connector ITM'

    def add_customer(self, vals):
        url_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('accounting_setup_id.active', '=', True), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in ITM Accounting Setup!')

        url = url_obj.variable_value
        headers = {
            'Content-Type': 'application/json',
        }
        req_data = self.request_parser_customer(vals)
        _logger.info('ITM Request Add Customer: %s', req_data)
        if vals.get('accounting_queue_id'):
            queue_obj = self.env['tt.accounting.queue'].browse(int(vals['accounting_queue_id']))
            if queue_obj:
                queue_obj.write({
                    'request': req_data
                })
        # res = util.send_request_json(self._get_web_hook('Sales%20Order'), post=vals, headers=headers)
        response = requests.post(url, data=req_data, headers=headers)
        res = self.response_parser_customer(response)

        if res['status'] == 'success':
            _logger.info('ITM Insert Customer Success')
            if res['content'].get('Data') and res['content']['Data'].get('dsAPIMethod1') and vals.get('seq_id'):
                for cust_resp in res['content']['Data']['dsAPIMethod1']:
                    cust_parent_obj = self.env['tt.customer.parent'].search([('seq_id', '=', vals['seq_id'])], limit=1)
                    if cust_parent_obj:
                        cust_parent_obj[0].write({
                            'accounting_uid': cust_resp.get('ContactCD') and str(cust_resp['ContactCD']) or ''
                        })
        else:
            _logger.info('ITM Insert Customer Failed')
        _logger.info(res)

        return res

    def request_parser_customer(self, request):
        live_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('accounting_setup_id.active', '=', True), ('variable_name', '=', 'live_id')], limit=1)
        if not live_id_obj:
            raise Exception('Please provide a variable with the name "live_id" in ITM Accounting Setup!')

        live_id = live_id_obj.variable_value
        req = {
            "LiveID": live_id,
            "MethodName": "TSystem..AP000_CreateContact",
            "Params": [
                {
                    "ParamName": "ContactCd",
                    "ParamValue": request.get('seq_id') and request['seq_id'] or ""
                },
                {
                    "ParamName": "Name",
                    "ParamValue": request.get('customer_parent_name') and "'%s'" % request['customer_parent_name'] or ""
                },
                {
                    "ParamName": "Fullname",
                    "ParamValue": request.get('customer_parent_name') and "'%s'" % request['customer_parent_name'] or ""
                },
                {
                    "ParamName": "UniqueCd",
                    "ParamValue": request.get('seq_id') and request['seq_id'] or ""
                }
            ]
        }
        if not self.validate_request_customer(req):
            raise Exception('Request cannot be sent because some field requirements are not met.')

        return json.dumps(req)

    def response_parser_customer(self, response):
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
        else:
            res['content'] = {}
        if res['content'].get('Messages'):
            if all(msg.get('Type', '') == 'SUCCESS' for msg in res['content']['Messages']):
                status = 'success'
            elif any(msg.get('Type', '') == 'SUCCESS' for msg in res['content']['Messages']):
                status = 'partial'
            else:
                status = 'failed'
        else:
            status = 'failed'
        res.update({
            'status': status,
        })
        return res

    def validate_request_customer(self, vals):
        validated = True
        missing_fields = []
        checked_fields_phase1 = ['LiveID', 'MethodName', 'Params']
        for rec in checked_fields_phase1:
            if not vals.get(rec):
                validated = False
                missing_fields.append(rec)
        if validated:
            checked_fields_phase2 = {
                'ContactCd': False,
                'Name': False,
                'Fullname': False,
                'UniqueCd': False
            }
            for rec in vals['Params']:
                if rec.get('ParamName') in checked_fields_phase2.keys():
                    checked_fields_phase2.update({
                        rec['ParamName']: True
                    })
                    if not rec.get('ParamValue'):
                        validated = False
                        missing_fields.append(rec['ParamName'])
            for key, val in checked_fields_phase2.items():
                if not val:
                    validated = False
                    missing_fields.append(key)
        if missing_fields:
            _logger.error('ITM accounting create customer request missing or empty fields: %s' % ', '.join(missing_fields))
        return validated

    def add_sales_order(self, vals):
        url_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(vals['ho_id'])), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in ITM Accounting Setup!')

        url = url_obj.variable_value
        headers = {
            'Content-Type': 'application/json',
        }
        req_data = self.request_parser(vals)
        _logger.info('ITM Request Add Sales Order: %s', req_data)
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
            _logger.info('ITM Insert Success')
        else:
            _logger.info('ITM Insert Failed')
        _logger.info(res)

        return res

    def request_parser(self, request):
        live_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', 'live_id')], limit=1)
        if not live_id_obj:
            raise Exception('Please provide a variable with the name "live_id" in ITM Accounting Setup!')
        trans_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', 'trans_id')], limit=1)
        if not trans_id_obj:
            raise Exception('Please provide a variable with the name "trans_id" in ITM Accounting Setup!')
        customer_code_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', 'customer_code')], limit=1)
        if not customer_code_obj:
            raise Exception('Please provide a variable with the name "customer_code" in ITM Accounting Setup!')
        item_key_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', 'item_key')], limit=1)
        if not item_key_obj:
            raise Exception('Please provide a variable with the name "item_key" in ITM Accounting Setup!')
        always_use_contactcd = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', 'always_use_contactcd')], limit=1)

        live_id = live_id_obj.variable_value
        trans_id = trans_id_obj.variable_value
        item_key = item_key_obj.variable_value
        if always_use_contactcd and always_use_contactcd.variable_value:
            use_contact_cd = True
        else:
            use_contact_cd = False
        customer_name = ''
        if customer_code_obj.variable_value == 'dynamic_customer_code':
            customer_code = ''
            if request.get('customer_parent_id'):
                customer_obj = self.env['tt.customer.parent'].browse(int(request['customer_parent_id']))
                try:
                    if customer_obj.accounting_uid:
                        customer_code = customer_obj.accounting_uid
                    else:
                        use_contact_cd = True
                        customer_code = customer_obj.seq_id
                    customer_name = customer_obj.name
                except:
                    customer_code = ''
        else:
            customer_code = int(customer_code_obj.variable_value)
        is_ho_transaction = False
        if request.get('agent_id'):
            agent_obj = self.env['tt.agent'].browse(int(request['agent_id']))
            if agent_obj and agent_obj.is_ho_agent:
                is_ho_transaction = True
        if request['category'] == 'reservation':
            include_service_taxes = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', 'is_include_service_taxes')], limit=1)
            pnr_list = request.get('pnr') and request['pnr'].split(', ') or []
            provider_list = []
            supplier_list = []
            idx = 0
            for prov in request['provider_bookings']:
                sup_search_param = [('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('provider_id.code', '=', prov['provider'])]
                if request.get('sector_type'):
                    if request['sector_type'] == 'Domestic':
                        temp_product_search = ('variable_name', '=', '%s_domestic_prod' % prov['provider'])
                    else:
                        temp_product_search = ('variable_name', '=', '%s_international_prod' % prov['provider'])
                    sector_based_product = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), temp_product_search], limit=1)
                    if sector_based_product:
                        sup_search_param.append(('product_code', '=', sector_based_product[0].variable_value))

                supplier_obj = self.env['tt.accounting.setup.suppliers'].search(sup_search_param, limit=1)
                if supplier_obj:
                    supplier_list.append({
                        'supplier_code': supplier_obj.supplier_code or '',
                        'supplier_name': supplier_obj.supplier_name or ''
                    })
                if request['provider_type'] == 'airline':
                    journey_list = []
                    journ_idx = 0
                    first_carrier_name = ''
                    for journ in prov['journeys']:
                        for segm in journ['segments']:
                            journey_list.append({
                                "itin": journ_idx + 1,
                                "CarrierCode": segm['carrier_code'],
                                "FlightNumber": segm['carrier_number'],
                                "DateTimeDeparture": segm['departure_date'],
                                "DateTimeArrival": segm['arrival_date'],
                                "Departure": segm['origin'],
                                "ClassNumber": segm['cabin_class'],
                                "Arrival": segm['destination']
                            })
                            if not first_carrier_name:
                                first_carrier_name = segm['carrier_name']
                            journ_idx += 1

                    for pax_idx, pax in enumerate(prov['tickets']):
                        if pax.get('ticket_number'):
                            if len(pax['ticket_number']) >= 13:
                                pax_tick = '%s-%s' % (pax['ticket_number'][:3], pax['ticket_number'][3:])
                            else:
                                pax_tick = pax['ticket_number']
                        else:
                            if journey_list and journey_list[0]['CarrierCode'] in ['QG','QZ']:
                                pax_tick = '%s-%s%s' % (journey_list[0]['CarrierCode'], prov['pnr'], f'{pax_idx+1:06d}')
                            else:
                                pax_tick = ''
                        pax_list = [{
                            "PassangerName": pax['passenger'],
                            "TicketNumber": pax_tick.replace(' ', ''),
                            "Gender": 1,
                            "Nationality": "ID"
                        }]

                        if is_ho_transaction:
                            ho_prof = pax.get('total_commission') and pax['total_commission'] or 0
                        else:
                            ho_prof = pax.get('ho_commission') and pax['ho_commission'] or 0
                            if pax.get('parent_agent_commission'):
                                ho_prof += pax['parent_agent_commission']  # update 12 Juni 2023, karena KCBJ minta profit yang dikirim ke ITM ditambah profit rodex (parent agent)

                        pax_setup = {
                            'ho_profit': ho_prof,
                            'agent_profit': pax.get('agent_commission') and pax['agent_commission'] or 0,
                            'total_comm': pax.get('total_commission') and pax['total_commission'] or 0,
                            'total_nta': pax.get('total_nta') and pax['total_nta'] or 0,
                            'agent_nta': pax.get('agent_nta') and pax['agent_nta'] or 0
                        }

                        vat_var_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', '%s_vat_var' % request['provider_type'])], limit=1)
                        vat_perc_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', '%s_vat_percentage' % request['provider_type'])], limit=1)
                        if not vat_var_obj or not vat_perc_obj:
                            _logger.info('Please set both {provider_type_code}_vat_var and {provider_type_code}_vat_percentage variables.')
                            vat = 0
                        else:
                            temp_vat_var = pax_setup.get(vat_var_obj.variable_value) and pax_setup[vat_var_obj.variable_value] or 0
                            vat = round(temp_vat_var * float(vat_perc_obj.variable_value) / 100)

                        temp_sales = pax_setup['agent_nta']
                        if is_ho_transaction:
                            temp_sales += ho_prof
                        # total cost = Total NTA
                        # total sales = Agent NTA (kalo HO + total commission)
                        # rumus lama: "Sales": pax.get('agent_nta') and (pax['agent_nta'] - (ho_prof * 9.9099 / 100)) or 0
                        provider_dict = {
                            "ItemNo": idx + 1,
                            "ProductCode": supplier_obj.product_code or '',
                            "ProductName": supplier_obj.product_name or '',
                            "CarrierCode": journey_list and journey_list[0]['CarrierCode'] or '',
                            "CArrierName": first_carrier_name or '',
                            "Description": prov['pnr'],
                            "Quantity": 1,
                            "Cost": pax_setup['total_nta'],
                            "Profit": pax_setup['ho_profit'] - vat,
                            "ServiceFee": 0,
                            "VAT": vat,
                            "Sales": temp_sales,
                            "Itin": journey_list,
                            "Pax": pax_list
                        }
                        if include_service_taxes and include_service_taxes.variable_value:
                            service_tax_list = []
                            for sct in pax['tax_service_charges']:
                                service_tax_list.append({
                                    "ServiceTax_string": sct['charge_code'],
                                    "ServiceTax_amount": sct['amount']
                                })
                            provider_dict.update({
                                "ServiceTaxes": service_tax_list
                            })
                        provider_list.append(provider_dict)
                        idx += 1

                elif request['provider_type'] == 'train':
                    journey_list = []
                    journ_idx = 0
                    first_carrier_name = ''
                    for journ in prov['journeys']:
                        journey_list.append({
                            "itin": journ_idx + 1,
                            "CarrierCode": journ['carrier_code'],
                            "FlightNumber": journ['carrier_number'],
                            "DateTimeDeparture": journ['departure_date'],
                            "DateTimeArrival": journ['arrival_date'],
                            "Departure": journ['origin'],
                            "ClassNumber": journ['cabin_class'],
                            "Arrival": journ['destination']
                        })
                        if not first_carrier_name:
                            first_carrier_name = journ['carrier_name']
                        journ_idx += 1

                    for pax_idx, pax in enumerate(prov['tickets']):
                        pax_list = [{
                            "PassangerName": pax['passenger'],
                            "TicketNumber": pax.get('ticket_number') and pax['ticket_number'] or '',
                            "Gender": 1,
                            "Nationality": "ID"
                        }]

                        if is_ho_transaction:
                            ho_prof = pax.get('total_commission') and pax['total_commission'] or 0
                        else:
                            ho_prof = pax.get('ho_commission') and pax['ho_commission'] or 0
                            if pax.get('parent_agent_commission'):
                                ho_prof += pax['parent_agent_commission']  # update 12 Juni 2023, karena KCBJ minta profit yang dikirim ke ITM ditambah profit rodex (parent agent)

                        pax_setup = {
                            'ho_profit': ho_prof,
                            'agent_profit': pax.get('agent_commission') and pax['agent_commission'] or 0,
                            'total_comm': pax.get('total_commission') and pax['total_commission'] or 0,
                            'total_nta': pax.get('total_nta') and pax['total_nta'] or 0,
                            'agent_nta': pax.get('agent_nta') and pax['agent_nta'] or 0
                        }

                        vat_var_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', '%s_vat_var' % request['provider_type'])], limit=1)
                        vat_perc_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', '%s_vat_percentage' % request['provider_type'])], limit=1)
                        if not vat_var_obj or not vat_perc_obj:
                            _logger.info('Please set both {provider_type_code}_vat_var and {provider_type_code}_vat_percentage variables.')
                            vat = 0
                        else:
                            temp_vat_var = pax_setup.get(vat_var_obj.variable_value) and pax_setup[vat_var_obj.variable_value] or 0
                            vat = round(temp_vat_var * float(vat_perc_obj.variable_value) / 100)

                        temp_sales = pax_setup['agent_nta']
                        if is_ho_transaction:
                            temp_sales += ho_prof
                        # total cost = Total NTA
                        # total sales = Agent NTA
                        # rumus lama: "Sales": pax.get('agent_nta') and (pax['agent_nta'] - (ho_prof * 9.9099 / 100)) or 0
                        provider_dict = {
                            "ItemNo": idx + 1,
                            "ProductCode": supplier_obj.product_code or '',
                            "ProductName": supplier_obj.product_name or '',
                            "CarrierCode": journey_list and journey_list[0]['CarrierCode'] or '',
                            "CArrierName": first_carrier_name or '',
                            "Description": prov['pnr'],
                            "Quantity": 1,
                            "Cost": pax_setup['total_nta'],
                            "Profit": pax_setup['ho_profit'] - vat,
                            "ServiceFee": 0,
                            "VAT": vat,
                            "Sales": temp_sales,
                            "Itin": journey_list,
                            "Pax": pax_list
                        }
                        if include_service_taxes and include_service_taxes.variable_value:
                            service_tax_list = []
                            for sct in pax['tax_service_charges']:
                                service_tax_list.append({
                                    "ServiceTax_string": sct['charge_code'],
                                    "ServiceTax_amount": sct['amount']
                                })
                            provider_dict.update({
                                "ServiceTaxes": service_tax_list
                            })
                        provider_list.append(provider_dict)
                        idx += 1

                elif request['provider_type'] == 'hotel':
                    if is_ho_transaction:
                        ho_prof = prov.get('total_commission') and prov['total_commission'] or 0
                    else:
                        ho_prof = prov.get('ho_commission') and prov['ho_commission'] or 0
                        if prov.get('parent_agent_commission'):
                            ho_prof += prov['parent_agent_commission']  # update 12 Juni 2023, karena KCBJ minta profit yang dikirim ke ITM ditambah profit rodex (parent agent)

                    prov_setup = {
                        'ho_profit': ho_prof,
                        'agent_profit': prov.get('agent_commission') and prov['agent_commission'] or 0,
                        'total_comm': prov.get('total_commission') and prov['total_commission'] or 0,
                        'total_nta': prov.get('total_nta') and prov['total_nta'] or 0,
                        'agent_nta': prov.get('agent_nta') and prov['agent_nta'] or 0
                    }

                    pax_list = []
                    for pax_idx, pax in enumerate(prov['passengers']):
                        pax_list.append({
                            "PassangerName": pax['name'],
                            "TicketNumber": '',
                            "Gender": 1,
                            "Nationality": pax['nationality_code']
                        })

                    vat_var_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', '%s_vat_var' % request['provider_type'])], limit=1)
                    vat_perc_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', '%s_vat_percentage' % request['provider_type'])], limit=1)
                    if not vat_var_obj or not vat_perc_obj:
                        _logger.info('Please set both {provider_type_code}_vat_var and {provider_type_code}_vat_percentage variables.')
                        vat = 0
                    else:
                        temp_vat_var = prov_setup.get(vat_var_obj.variable_value) and prov_setup[vat_var_obj.variable_value] or 0
                        vat = round(temp_vat_var * float(vat_perc_obj.variable_value) / 100)

                    journey_list = [{
                        "itin": 1,
                        "CarrierCode": prov['provider_code'],
                        "FlightNumber": prov['hotel_name'],
                        "DateTimeDeparture": prov['checkin_date'],
                        "DateTimeArrival": prov['checkout_date'],
                        "Departure": '',
                        "ClassNumber": '',
                        "Arrival": ''
                    }]
                    for room_idx, room in enumerate(prov['rooms']):
                        temp_sales = prov_setup['agent_nta'] / len(prov['rooms']) / request['nights']
                        if is_ho_transaction:
                            temp_sales += ho_prof / len(prov['rooms']) / request['nights']
                        provider_dict = {
                            "ItemNo": idx + 1,
                            "ProductCode": supplier_obj.product_code or '',
                            "ProductName": supplier_obj.product_name or '',
                            "CarrierCode": journey_list and journey_list[0]['CarrierCode'] or '',
                            "CArrierName": prov['provider_name'],
                            "Description": prov['pnr'],
                            "Hotel_RoomType": room.get('room_type') and room['room_type'] or '',
                            "Hotel_ServiceType": room.get('meal_type') and room['meal_type'] or '',
                            "Hotel_CityCD": prov.get('hotel_city') and prov['hotel_city'] or '',
                            "Quantity": 1,
                            "Cost": prov_setup['total_nta'] / len(prov['rooms']) / request['nights'],
                            "Profit": (prov_setup['ho_profit'] - vat) / len(prov['rooms']) / request['nights'],
                            "ServiceFee": 0,
                            "VAT": vat / len(prov['rooms']) / request['nights'],
                            "Sales": temp_sales,
                            "Itin": journey_list,
                            "Pax": pax_list
                        }
                        if include_service_taxes and include_service_taxes.variable_value:
                            service_tax_list = []
                            for sct in prov['tax_service_charges']:
                                service_tax_list.append({
                                    "ServiceTax_string": sct['charge_code'],
                                    "ServiceTax_amount": sct['amount'] / len(prov['rooms']) / request['nights']
                                })
                            provider_dict.update({
                                "ServiceTaxes": service_tax_list
                            })
                        provider_list.append(provider_dict)
                        idx += 1

            total_sales = request.get('agent_nta', 0)
            if is_ho_transaction:
                total_sales += request.get('total_commission') and request['total_commission'] or 0
                # total_sales += request.get('total_channel_upsell') and request['total_channel_upsell'] or 0

            uniquecode = '%s_%s%s' % (request.get('order_number', ''), datetime.now().strftime('%m%d%H%M%S'), chr(randrange(65,90)))
            travel_file_data = {
                "TypeTransaction": 111,
                "TransactionCode": "%s_%s" % ('_'.join(pnr_list), request.get('order_number', '')),
                "Date": "",
                "ReffCode": request.get('order_number', ''),
                "CustomerCode": "",
                "CustomerName": customer_name,
                "TransID": trans_id,
                "Description": '_'.join(pnr_list),
                "ActivityDate": "",
                "SupplierCode": supplier_list and supplier_list[0]['supplier_code'] or '',
                "SupplierName": supplier_list and supplier_list[0]['supplier_name'] or '',
                "TotalCost": request.get('total_nta', 0),
                "TotalSales": total_sales,
                "Source": "",
                "UserName": "",
                "SalesID": 0,
                item_key: provider_list
            }
            if use_contact_cd:
                travel_file_data.update({
                    "ContactCD": customer_code,
                })
            else:
                travel_file_data.update({
                    "CustomerCode": customer_code,
                })
            req = {
                "LiveID": live_id,
                "AccessMode": "",
                "UniqueCode": uniquecode,
                "TravelFile": travel_file_data,
                "MethodSettlement": "NONE"
            }
            if not self.validate_request(req):
                raise Exception('Request cannot be sent because some field requirements are not met.')
        elif request['category'] == 'reschedule':
            include_service_taxes = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), ('variable_name', '=', 'is_include_service_taxes')], limit=1)
            pnr_str = request['referenced_pnr'].replace(', ', '_')
            if request.get('new_pnr') and request['new_pnr'] != request['referenced_pnr']:
                pnr_str += '__%s' % request['new_pnr'].replace(', ', '_')
            resch_provider_list = []
            adm_fee_total = request.get('admin_fee') and request['admin_fee'] or 0
            adm_fee_agent = 0
            adm_fee_ho = 0
            for resch_line in request['reschedule_lines']:
                if resch_line.get('provider'):
                    resch_provider_list.append(resch_line['provider'])
                adm_fee_agent += resch_line.get('admin_fee_agent') and resch_line['admin_fee_agent'] or 0
                adm_fee_ho += resch_line.get('admin_fee_ho') and resch_line['admin_fee_ho'] or 0
            total_sales = agent_nta = request.get('reschedule_amount', 0)
            if is_ho_transaction:
                total_sales += adm_fee_total
                tot_ho_profit = tot_agent_profit = adm_fee_total
            else:
                total_sales += adm_fee_ho
                agent_nta += adm_fee_ho
                tot_ho_profit = adm_fee_ho
                tot_agent_profit = adm_fee_agent
            used_provider_bookings = []
            for prov in request['provider_bookings']:
                if prov.get('provider') and prov['provider'] in resch_provider_list:
                    used_provider_bookings.append(prov)
            provider_list = []
            supplier_list = []
            for idx, prov in enumerate(used_provider_bookings):
                sup_search_param = [('accounting_setup_id.accounting_provider', '=', 'itm'),
                                    ('accounting_setup_id.active', '=', True),
                                    ('accounting_setup_id.ho_id', '=', int(request['ho_id'])),
                                    ('provider_id.code', '=', prov['provider'])]
                if request['reservation_data'].get('sector_type'):
                    if request['reservation_data']['sector_type'] == 'Domestic':
                        temp_product_search = ('variable_name', '=', '%s_domestic_prod' % prov['provider'])
                    else:
                        temp_product_search = ('variable_name', '=', '%s_international_prod' % prov['provider'])
                    sector_based_product = self.env['tt.accounting.setup.variables'].search(
                        [('accounting_setup_id.accounting_provider', '=', 'itm'),
                         ('accounting_setup_id.active', '=', True),
                         ('accounting_setup_id.ho_id', '=', int(request['ho_id'])), temp_product_search], limit=1)
                    if sector_based_product:
                        sup_search_param.append(('product_code', '=', sector_based_product[0].variable_value))

                supplier_obj = self.env['tt.accounting.setup.suppliers'].search(sup_search_param, limit=1)
                if supplier_obj:
                    supplier_list.append({
                        'supplier_code': supplier_obj.supplier_code or '',
                        'supplier_name': supplier_obj.supplier_name or ''
                    })

                journey_list = []
                journ_idx = 0
                first_carrier_name = ''
                for journ in prov['journeys']:
                    for segm in journ['segments']:
                        journey_list.append({
                            "itin": journ_idx + 1,
                            "CarrierCode": segm['carrier_code'],
                            "FlightNumber": segm['carrier_number'],
                            "DateTimeDeparture": segm['departure_date'],
                            "DateTimeArrival": segm['arrival_date'],
                            "Departure": segm['origin'],
                            "ClassNumber": segm['cabin_class'],
                            "Arrival": segm['destination']
                        })
                        if not first_carrier_name:
                            first_carrier_name = segm['carrier_name']
                        journ_idx += 1

                pax_list = []
                for pax_idx, pax in enumerate(prov['tickets']):
                    if pax.get('ticket_number'):
                        if len(pax['ticket_number']) > 3:
                            pax_tick = '%s-%s' % (pax['ticket_number'][:3], pax['ticket_number'][3:])
                        else:
                            pax_tick = pax['ticket_number']
                    else:
                        if journey_list and journey_list[0]['CarrierCode'] in ['QG', 'QZ']:
                            pax_tick = '%s-%s%s' % (journey_list[0]['CarrierCode'], prov['pnr'], f'{pax_idx + 1:06d}')
                        else:
                            pax_tick = ''
                    pax_list.append({
                        "PassangerName": pax['passenger'],
                        "TicketNumber": pax_tick.replace(' ', ''),
                        "Gender": 1,
                        "Nationality": "ID"
                    })

                vat_var_obj = self.env['tt.accounting.setup.variables'].search(
                    [('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True),
                     ('accounting_setup_id.ho_id', '=', int(request['ho_id'])),
                     ('variable_name', '=', '%s_vat_var' % request['reservation_data']['provider_type'])], limit=1)
                vat_perc_obj = self.env['tt.accounting.setup.variables'].search(
                    [('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True),
                     ('accounting_setup_id.ho_id', '=', int(request['ho_id'])),
                     ('variable_name', '=', '%s_vat_percentage' % request['reservation_data']['provider_type'])], limit=1)
                if not vat_var_obj or not vat_perc_obj:
                    _logger.info('Please set both {provider_type_code}_vat_var and {provider_type_code}_vat_percentage variables.')
                    vat = 0
                else:
                    if vat_var_obj.variable_value == 'ho_profit':
                        vat = round((tot_ho_profit / len(pax_list) / len(used_provider_bookings)) * float(vat_perc_obj.variable_value) / 100)
                    elif vat_var_obj.variable_value == 'agent_profit':
                        vat = round((tot_agent_profit / len(pax_list) / len(used_provider_bookings)) * float(vat_perc_obj.variable_value) / 100)
                    elif vat_var_obj.variable_value == 'total_comm':
                        vat = round((adm_fee_total / len(pax_list) / len(used_provider_bookings)) * float(vat_perc_obj.variable_value) / 100)
                    else:
                        vat = 0

                provider_dict = {
                    "ItemNo": idx + 1,
                    "ProductCode": supplier_obj.product_code or '',
                    "ProductName": supplier_obj.product_name or '',
                    "CarrierCode": journey_list and journey_list[0]['CarrierCode'] or '',
                    "CArrierName": first_carrier_name or '',
                    "Description": prov['pnr'],
                    "Quantity": 1,
                    "Cost": request.get('reschedule_amount') and request['reschedule_amount'] / len(pax_list) / len(used_provider_bookings) or 0,
                    "Profit": (tot_ho_profit / len(pax_list) / len(used_provider_bookings)) - vat,
                    "ServiceFee": 0,
                    "VAT": vat,
                    "Sales": total_sales / len(pax_list) / len(used_provider_bookings),
                    "Itin": journey_list,
                    "Pax": pax_list
                }
                if include_service_taxes and include_service_taxes.variable_value:
                    service_tax_list = [{
                        "ServiceTax_string": 'tax',
                        "ServiceTax_amount": agent_nta + tot_agent_profit - tot_ho_profit
                    }]
                    provider_dict.update({
                        "ServiceTaxes": service_tax_list
                    })
                provider_list.append(provider_dict)
            uniquecode = '%s_%s%s' % (request.get('order_number', ''), datetime.now().strftime('%m%d%H%M%S'), chr(randrange(65, 90)))
            travel_file_data = {
                "TypeTransaction": 111,
                "TransactionCode": "%s_%s" % (pnr_str, request.get('reservation_name', '')),
                "Date": "",
                "ReffCode": request.get('order_number', ''),
                "CustomerCode": "",
                "CustomerName": customer_name,
                "TransID": trans_id,
                "Description": "%s for %s" % (request['reschedule_type'], pnr_str),
                "ActivityDate": "",
                "SupplierCode": supplier_list and supplier_list[0]['supplier_code'] or '',
                "SupplierName": supplier_list and supplier_list[0]['supplier_name'] or '',
                "TotalCost": request.get('reschedule_amount', 0),
                "TotalSales": total_sales,
                "Source": "",
                "UserName": "",
                "SalesID": 0,
                item_key: provider_list
            }
            if use_contact_cd:
                travel_file_data.update({
                    "ContactCD": customer_code,
                })
            else:
                travel_file_data.update({
                    "CustomerCode": customer_code,
                })
            req = {
                "LiveID": live_id,
                "AccessMode": "",
                "UniqueCode": uniquecode,
                "TravelFile": travel_file_data,
                "MethodSettlement": "NONE"
            }
            if not self.validate_request(req):
                raise Exception('Request cannot be sent because some field requirements are not met.')
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
        if res['content'].get('Messages'):
            if all(msg.get('Type', '') == 'SUCCESS' for msg in res['content']['Messages']):
                status = 'success'
            elif any(msg.get('Type', '') == 'SUCCESS' for msg in res['content']['Messages']):
                status = 'partial'
            else:
                status = 'failed'
        else:
            status = 'failed'
        res.update({
            'status': status,
        })
        return res

    def validate_request(self, vals):
        validated = True
        missing_fields = []
        checked_fields_phase1 = ['LiveID', 'UniqueCode', 'TravelFile']
        for rec in checked_fields_phase1:
            if not vals.get(rec):
                validated = False
                missing_fields.append(rec)
        if validated:
            checked_fields_phase2 = ['TransactionCode', 'ReffCode', 'CustomerCode']
            for rec in checked_fields_phase2:
                if not vals['TravelFile'].get(rec):
                    if rec == 'CustomerCode':
                        if not vals['TravelFile'].get('ContactCD'):
                            validated = False
                            missing_fields.append('TravelFile: CustomerCode / ContactCD')
                    else:
                        validated = False
                        missing_fields.append('TravelFile: %s' % rec)
        if missing_fields:
            _logger.error('ITM accounting request missing or empty fields: %s' % ', '.join(missing_fields))
        return validated
