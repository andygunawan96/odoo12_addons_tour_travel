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
            _logger.info('Insert Success')
        else:
            _logger.info('Insert Failed')
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
                raise Exception('Please provide a variable with the name "sourcetypeid" in ITM Accounting Setup!')
            source_type_id = source_type_id_obj.variable_value
            customer_id = 0
            customer_name = ''
            if request.get('customer_parent_id'):
                customer_obj = self.env['tt.customer.parent'].browse(int(request['customer_parent_id']))
                if customer_obj.accounting_uid:
                    customer_id = int(customer_obj.accounting_uid)
                if customer_obj.name:
                    customer_name = customer_obj.name
            ticket_itin_list = []
            ticket_itin_idx = 0
            ticket_list = []
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
                                "proddtlcode": request['sector_type'] == 'Domestic' and 'TKTD' or 'TKTI',
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
                            pax_tick = pax['ticket_number']
                            airline_id = len(pax['ticket_number']) > 3 and pax['ticket_number'][:3] or ''
                        else:
                            pax_tick = '%s_%s' % (prov['pnr'], str(pax_idx))
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

                        pax_setup = {
                            'ho_profit': pax.get('parent_agent_commission') and ho_prof + pax['parent_agent_commission'] or ho_prof,  # update 12 Juni 2023, karena KCBJ minta profit yang dikirim ke ITM ditambah profit rodex (parent agent)
                            'agent_profit': pax.get('agent_commission') and pax['agent_commission'] or 0,
                            'total_comm': pax.get('total_commission') and pax['total_commission'] or 0,
                            'total_nta': pax.get('total_nta') and pax['total_nta'] or 0,
                            'agent_nta': pax.get('agent_nta') and pax['agent_nta'] or 0
                        }

                        temp_sales = pax_setup['agent_nta']
                        if is_ho_transaction:
                            temp_sales += pax_setup['total_comm']

                        ticket_list.append({
                            {
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
                                "pubfare": 2513000.0000,
                                "airporttax": 822840.0000,
                                "commission": 75500.0000,
                                "servicefee": 65207.0,
                                "surcharge": 0.0000,
                                "markupamt": 0,
                                "sellpricenotax": 2437500.0000,
                                "nettfare": 2437500.0000,
                                "nettprice": 3260340.0000,
                                "sellprice": 3325547.0,
                                "currid": prov['currency'],
                                "pubfareccy": prov['currency'],
                                "nettcurrid": prov['currency'],
                                "commpercent": 0.0
                            }
                        })
            req = {
                "booking": {
                    "custid": customer_id,
                    "custcode": "",
                    "custname": customer_name,
                    "cctcname": "%s %s" % (request['contact']['title'], request['contact']['name']),
                    "cctcphone": request['contact']['phone'],
                    "cctcaddress": "testing ",
                    "email": request['contact']['email'],
                    "ref_invoice": "",
                    "ref_bookcode": request['order_number'],
                    "bookingext": request['order_number'],
                    "invoiceflag": False,
                    "sourcetypeid": source_type_id,
                    "printflag": False,
                    "autopaidbydp": False
                },
                "ticket_itin": ticket_itin_list,
                "ticket": ticket_list
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
        if res['content'].get('message') == 'SUCCESS':
            status = 'success'
        else:
            status = 'failed'
        res.update({
            'status': status,
        })
        return res
