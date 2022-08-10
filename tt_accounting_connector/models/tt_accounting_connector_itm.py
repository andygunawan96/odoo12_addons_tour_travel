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
        live_id_obj = self.env['tt.accounting.setup.variables'].search([('accounting_setup_id.accounting_provider', '=', 'itm'), ('variable_name', '=', 'live_id')], limit=1)
        if not live_id_obj:
            raise Exception('Please provide a variable with the name "live_id" in ITM Accounting Setup!')

        live_id = live_id_obj.variable_value
        if request['category'] == 'reservation':
            pnr_list = request.get('pnr') and request['pnr'].split(', ') or []
            provider_list = []
            supplier_list = []
            idx = 0
            for prov in request['provider_bookings']:
                if request['provider_type'] == 'airline':
                    supplier_obj = self.env['tt.accounting.setup.suppliers'].search(
                        [('accounting_setup_id.accounting_provider', '=', 'itm'),
                         ('provider_id.code', '=', prov['provider'])], limit=1)
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

                    for pax in prov['tickets']:
                        pax_tick = ''
                        if pax.get('ticket_number'):
                            if len(pax['ticket_number']) > 3:
                                pax_tick = '%s-%s' % (pax['ticket_number'][:3], pax['ticket_number'][3:])
                            else:
                                pax_tick = pax['ticket_number']
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

                        # total cost = Total NTA
                        # total sales = Agent NTA
                        # rumus lama: "Sales": pax.get('agent_nta') and (pax['agent_nta'] - (ho_prof * 9.9099 / 100)) or 0
                        provider_list.append({
                            "ItemNo": idx+1,
                            "ProductCode": supplier_obj.product_code or '',
                            "ProductName": supplier_obj.product_name or '',
                            "CarrierCode": journey_list and journey_list[0]['CarrierCode'] or '',
                            "CArrierName": first_carrier_name or '',
                            "Description": prov['pnr'],
                            "Quantity": 1,
                            "Cost": pax.get('total_nta', 0),
                            "Profit": ho_prof - round(ho_prof * 9.9099 / 100),
                            "ServiceFee": 0,
                            "VAT": round(ho_prof * 9.9099 / 100),
                            "Sales": pax.get('agent_nta', 0),
                            "Itin": journey_list,
                            "Pax": pax_list
                        })

                        idx += 1
            total_sales = request.get('agent_nta', 0)
            if int(request.get('agent_id', 0)) == self.env.ref('tt_base.rodex_ho').id:
                total_sales += request.get('total_channel_upsell', 0)

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
                    "SupplierCode": supplier_list and supplier_list[0]['supplier_code'] or '',
                    "SupplierName": supplier_list and supplier_list[0]['supplier_name'] or '',
                    "TotalCost": request.get('total_nta', 0),
                    "TotalSales": total_sales,
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
