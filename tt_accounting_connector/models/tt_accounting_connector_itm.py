from odoo import api, fields, models, _
import logging
import requests
import json
import base64
import time
from datetime import datetime

_logger = logging.getLogger(__name__)
# url = 'http://cloud1.suvarna-mi.com:1293/Data15/RunTravelfileV3'
# live_id = 'b02849bd-788f-401e-a039-9afba72e3c9d'
# product_code = 'AVINTBSP'


class AccountingConnectorITM(models.Model):
    _name = 'tt.accounting.connector.itm'
    _description = 'Accounting Connector ITM'

    # cuma support airline for now
    def add_sales_order(self, vals):
        url_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in ITM Accounting Setup!')

        url = url_obj.variable_value
        headers = {
            'Content-Type': 'application/json',
        }
        req_data = self.request_parser(vals)
        _logger.info('ITM Request Add Sales Order: %s', req_data)
        # res = util.send_request_json(self._get_web_hook('Sales%20Order'), post=vals, headers=headers)
        response = requests.post(url, data=req_data, headers=headers)
        res = self.response_parser(response)

        if res['status'] == 'success':
            _logger.info('Insert Success')
        else:
            _logger.info('Insert Failed')
        _logger.info(res)

        return res

    def request_parser(self, request):
        live_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', 'live_id')], limit=1)
        if not live_id_obj:
            raise Exception('Please provide a variable with the name "live_id" in ITM Accounting Setup!')
        trans_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', 'trans_id')], limit=1)
        if not trans_id_obj:
            raise Exception('Please provide a variable with the name "trans_id" in ITM Accounting Setup!')
        customer_code_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', 'customer_code')], limit=1)
        if not customer_code_obj:
            raise Exception('Please provide a variable with the name "customer_code" in ITM Accounting Setup!')
        item_key_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', 'item_key')], limit=1)
        if not item_key_obj:
            raise Exception('Please provide a variable with the name "item_key" in ITM Accounting Setup!')

        live_id = live_id_obj.variable_value
        trans_id = trans_id_obj.variable_value
        item_key = item_key_obj.variable_value
        if customer_code_obj.variable_value == 'dynamic_customer_code':
            customer_code = ''
            if request.get('customer_parent_id'):
                customer_obj = self.env['tt.customer.parent'].browse(int(request['customer_parent_id']))
                try:
                    customer_code = customer_obj.seq_id
                except:
                    customer_code = ''
        else:
            customer_code = int(customer_code_obj.variable_value)
        if request['category'] == 'reservation':
            include_service_taxes = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', 'is_include_service_taxes')], limit=1)
            pnr_list = request.get('pnr') and request['pnr'].split(', ') or []
            provider_list = []
            supplier_list = []
            idx = 0
            for prov in request['provider_bookings']:
                sup_search_param = [('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('provider_id.code', '=', prov['provider'])]
                if request.get('sector_type'):
                    if request['sector_type'] == 'Domestic':
                        temp_product_search = ('variable_name', '=', 'domestic_product')
                    else:
                        temp_product_search = ('variable_name', '=', 'international_product')
                    sector_based_product = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), temp_product_search], limit=1)
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
                            if len(pax['ticket_number']) > 3:
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
                            "TicketNumber": pax_tick,
                            "Gender": 1,
                            "Nationality": "ID"
                        }]

                        if pax.get('total_channel_upsell') and int(request.get('agent_id', 0)) == self.env.ref('tt_base.rodex_ho').id:
                            ho_prof = pax.get('ho_commission') and pax['ho_commission'] + pax['total_channel_upsell'] or pax['total_channel_upsell']
                        else:
                            ho_prof = pax.get('ho_commission') and pax['ho_commission'] or 0

                        pax_setup = {
                            'ho_profit': ho_prof,
                            'total_nta': pax.get('total_nta') and pax['total_nta'] or 0,
                            'agent_nta': pax.get('agent_nta') and pax['agent_nta'] or 0
                        }

                        vat_var_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', '%s_vat_var' % request['provider_type'])], limit=1)
                        vat_perc_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', '%s_vat_percentage' % request['provider_type'])], limit=1)
                        if not vat_var_obj or not vat_perc_obj:
                            _logger.info('Please set both {provider_type_code}_vat_var and {provider_type_code}_vat_percentage variables.')
                            vat = 0
                        else:
                            temp_vat_var = pax_setup.get(vat_var_obj.variable_value) and pax_setup[vat_var_obj.variable_value] or 0
                            vat = round(temp_vat_var * float(vat_perc_obj.variable_value) / 100)

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
                            "Sales": pax_setup['agent_nta'],
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

                        if pax.get('total_channel_upsell') and int(request.get('agent_id', 0)) == self.env.ref('tt_base.rodex_ho').id:
                            ho_prof = pax.get('ho_commission') and pax['ho_commission'] + pax['total_channel_upsell'] or pax['total_channel_upsell']
                        else:
                            ho_prof = pax.get('ho_commission') and pax['ho_commission'] or 0

                        pax_setup = {
                            'ho_profit': ho_prof,
                            'total_nta': pax.get('total_nta') and pax['total_nta'] or 0,
                            'agent_nta': pax.get('agent_nta') and pax['agent_nta'] or 0
                        }

                        vat_var_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', '%s_vat_var' % request['provider_type'])], limit=1)
                        vat_perc_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', '%s_vat_percentage' % request['provider_type'])], limit=1)
                        if not vat_var_obj or not vat_perc_obj:
                            _logger.info('Please set both {provider_type_code}_vat_var and {provider_type_code}_vat_percentage variables.')
                            vat = 0
                        else:
                            temp_vat_var = pax_setup.get(vat_var_obj.variable_value) and pax_setup[vat_var_obj.variable_value] or 0
                            vat = round(temp_vat_var * float(vat_perc_obj.variable_value) / 100)

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
                            "Sales": pax_setup['agent_nta'],
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
                    prov_setup = {
                        'ho_profit': 0,
                        'total_nta': 0,
                        'agent_nta': 0
                    }
                    if prov.get('total_channel_upsell') and int(request.get('agent_id', 0)) == self.env.ref('tt_base.rodex_ho').id:
                        ho_prof = prov.get('ho_commission') and prov['ho_commission'] + prov['total_channel_upsell'] or prov['total_channel_upsell']
                    else:
                        ho_prof = prov.get('ho_commission') and prov['ho_commission'] or 0

                    prov_setup['ho_profit'] += ho_prof
                    prov_setup['total_nta'] += prov.get('total_nta') and prov['total_nta'] or 0
                    prov_setup['agent_nta'] += prov.get('agent_nta') and prov['agent_nta'] or 0

                    pax_list = []
                    for pax_idx, pax in enumerate(prov['passengers']):
                        pax_list.append({
                            "PassangerName": pax['name'],
                            "TicketNumber": '',
                            "Gender": 1,
                            "Nationality": pax['nationality_code']
                        })

                    vat_var_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', '%s_vat_var' % request['provider_type'])], limit=1)
                    vat_perc_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('accounting_setup_id.active', '=', True), ('variable_name', '=', '%s_vat_percentage' % request['provider_type'])], limit=1)
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
                            "Cost": prov_setup['total_nta'] / len(prov['rooms']),
                            "Profit": (prov_setup['ho_profit'] - vat) / len(prov['rooms']),
                            "ServiceFee": 0,
                            "VAT": vat / len(prov['rooms']),
                            "Sales": prov_setup['agent_nta'] / len(prov['rooms']),
                            "Itin": journey_list,
                            "Pax": pax_list
                        }
                        if include_service_taxes and include_service_taxes.variable_value:
                            service_tax_list = []
                            for sct in prov['tax_service_charges']:
                                service_tax_list.append({
                                    "ServiceTax_string": sct['charge_code'],
                                    "ServiceTax_amount": sct['amount'] / len(prov['rooms'])
                                })
                            provider_dict.update({
                                "ServiceTaxes": service_tax_list
                            })
                        provider_list.append(provider_dict)
                        idx += 1

            total_sales = request.get('agent_nta', 0)
            if int(request.get('agent_id', 0)) == self.env.ref('tt_base.rodex_ho').id:
                total_sales += request.get('total_channel_upsell') and request['total_channel_upsell'] or 0

            req = {
                "LiveID": live_id,
                "AccessMode": "",
                "UniqueCode": request.get('order_number', ''),
                "TravelFile": {
                    "TypeTransaction": 111,
                    "TransactionCode": "%s_%s" % ('_'.join(pnr_list), request.get('order_number', '')),
                    "Date": "",
                    "ReffCode": request.get('order_number', ''),
                    "CustomerCode": "",
                    "ContactCD": customer_code,
                    "CustomerName": "",
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
                },
                "MethodSettlement": "NONE"
            }
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
