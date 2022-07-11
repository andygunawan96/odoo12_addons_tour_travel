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
        url_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('variable_name', '=', 'url')], limit=1)
        if not url_obj:
            raise Exception('Please provide a variable with the name "url" in ITM Accounting Setup!')

        url = url_obj.variable_value
        headers = {
            'Content-Type': 'application/json',
        }
        req_data = self.request_parser(vals)
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
        live_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('variable_name', '=', 'live_id')], limit=1)
        if not live_id_obj:
            raise Exception('Please provide a variable with the name "live_id" in ITM Accounting Setup!')
        product_code_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('variable_name', '=', 'product_code')], limit=1)
        if not product_code_obj:
            raise Exception('Please provide a variable with the name "product_code" in ITM Accounting Setup!')

        live_id = live_id_obj.variable_value
        product_code = product_code_obj.variable_value
        if request['category'] == 'reservation':
            pnr_list = request.get('pnr') and request['pnr'].split(', ') or []
            provider_list = []
            for idx, prov in enumerate(request['provider_bookings']):
                if request['provider_type'] == 'airline':
                    journey_list = []
                    journ_idx = 0
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
                            journ_idx += 1
                    pax_list = []
                    for pax in prov['tickets']:
                        pax_list.append({
                            "PassangerName": pax['passenger'],
                            "TicketNumber": pax['ticket_number'],
                            "Gender": 1,
                            "Nationality": "ID"
                        })

                    if request.get('total_channel_upsell') and int(request.get('agent_id', 0)) == self.env.ref('tt_base.rodex_ho').id:
                        ho_prof = prov.get('ho_commission') and prov['ho_commission'] + request['total_channel_upsell'] or 0
                    else:
                        ho_prof = prov.get('ho_commission') and prov['ho_commission'] or 0
                    provider_list.append({
                        "ItemNo": idx+1,
                        "ProductCode": product_code,
                        "ProductName": "",
                        "CarrierCode": prov['provider'],
                        "CArrierName": "",
                        "Description": prov['pnr'],
                        "Quantity": 1,
                        "Cost": prov.get('agent_nta', 0),
                        "Profit": ho_prof - (ho_prof * 9.9099 / 100),
                        "ServiceFee": 0,
                        "VAT": ho_prof * 9.9099 / 100,
                        "Sales": prov.get('agent_nta') and (prov['agent_nta'] - (ho_prof * 9.9099 / 100)) or 0,
                        "Itin": journey_list,
                        "Pax": pax_list
                    })
            req = {
                "LiveID": live_id,
                "AccessMode": "",
                "UniqueCode": request.get('order_number', ''),
                "TravelFile": {
                    "TypeTransaction": 111,
                    "TransactionCode": "%s_%s" % ('_'.join(pnr_list), request.get('order_number', '')),
                    "Date": "",
                    "ReffCode": request.get('order_number', ''),
                    "CustomerCode": 9601,
                    "CustomerName": "",
                    "TransID": "48720",
                    "Description": '_'.join(pnr_list),
                    "ActivityDate": "",
                    "SupplierCode": "",
                    "SupplierName": "",
                    "TotalCost": 0,
                    "TotalSales": 0,
                    "Source": "",
                    "UserName": "",
                    "SalesID": 0,
                    "Item": provider_list
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
        if all(msg.get('Type', '') == 'SUCCESS' for msg in res['content']['Messages']):
            status = 'success'
        elif any(msg.get('Type', '') == 'SUCCESS' for msg in res['content']['Messages']):
            status = 'partial'
        else:
            status = 'failed'
        res.update({
            'status': status,
        })
        return res
