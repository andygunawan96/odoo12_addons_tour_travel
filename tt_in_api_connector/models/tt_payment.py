from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging
from datetime import datetime
import json
_logger = logging.getLogger(__name__)

class TtPaymentApiCon(models.Model):
    _name = 'tt.payment.api.con'
    _inherit = 'tt.api.con'

    table_name = 'payment.acquirer'

    def action_call(self, table_obj, action, data, context):
        if action == 'payment':
            if data['va_type'] == 'open':
                if self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0].state == 'open':
                    payment_acq_number_obj = self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0]
                    payment_acq_number_obj.fee = data['fee']
                    # check ada payment ref yg kembar ngga
                    if not self.env['tt.payment'].search([('reference', '=', data['payment_ref'])]):
                        # topup

                        agent_id = self.env['tt.agent'].browse(payment_acq_number_obj.agent_id.id)
                        context = {
                            'co_agent_id': agent_id.id,
                            'co_uid': self.env.ref('tt_base.base_top_up_admin').id
                        }
                        request = {
                            'amount': data['amount'],
                            'seq_id': payment_acq_number_obj.payment_acquirer_id.seq_id,
                            'currency_code': data['ccy'],
                            'payment_ref': data['payment_ref'],
                            'payment_seq_id': payment_acq_number_obj.payment_acquirer_id.seq_id
                        }

                        res = self.env['tt.top.up'].create_top_up_api(request,context, True)
                        if res['error_code'] == 0:
                            request = {
                                'virtual_account': data['virtual_account'],
                                'name': res['response']['name'],
                                'payment_ref': data['payment_ref'],
                                'fee': data['fee']
                            }
                            res = self.env['tt.top.up'].action_va_top_up(request, context, payment_acq_number_obj.id)
                    else:
                        res = ERR.get_error(500, additional_message="double payment")
                else:
                    res = ERR.get_error(500, additional_message="VA Not Found")
            elif data['va_type'] == 'close':
                res = ''
                #ganti ke done
                pay_acq_num = self.env['payment.acquirer.number'].search([('number', 'ilike', data['order_number'])])
                if pay_acq_num:
                    pay_acq_num[len(pay_acq_num)-1].state = 'done'
                    pay_acq_num[len(pay_acq_num)-1].fee_amount = float(data['fee'])
                agent_id = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])]).agent_id
                if not self.env['tt.payment'].search([('reference', '=', data['payment_ref'])]):
                    # topup
                    context = {
                        'co_agent_id': agent_id.id,
                        'co_uid': self.env.ref('tt_base.base_top_up_admin').id
                    }
                    request = {
                        'amount': data['amount'],
                        'currency_code': data['ccy'],
                        'payment_ref': data['payment_ref'],
                        'payment_seq_id': pay_acq_num.payment_acquirer_id.seq_id,
                        'fee': data['fee']
                    }

                    res = self.env['tt.top.up'].create_top_up_api(request,context, True)
                    if res['error_code'] == 0:
                        request = {
                            'virtual_account': data['virtual_account'],
                            'name': res['response']['name'],
                            'payment_ref': data['payment_ref'],
                            'fee': data['fee']
                        }
                        res = self.env['tt.top.up'].action_va_top_up(request, context, pay_acq_num.id)

                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number']), ('state', 'in', ['booked'])], limit=1)
                _logger.info(data['order_number'])
                if book_obj:
                    if book_obj.total == float(data['transaction_amount']):
                        values = {
                            "amount": book_obj.total,
                            "currency": book_obj.currency_id.name,
                            "co_uid": book_obj.user_id.id
                        }
                        res = ERR.get_no_error(values)
                    else:
                        res = ERR.get_error(additional_message='Price not same')
                else:
                    res = ERR.get_error(additional_message='Reservation Already Paid or Expired')
                try:
                    if res == '':
                        res = ERR.get_error(500, additional_message="double payment")
                except:
                    pass
            elif self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0].state == 'done':
                #close already done
                pass
            # payment_acq = self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])
        elif action == 'get_amount':
            book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number']), ('state', 'in', ['booked'])])
            if book_obj:
                different_time = book_obj.hold_date - datetime.now()
                different_time = int(different_time.seconds/60)
                if different_time > 60:
                    different_time = 55
                else:
                    different_time -= 5
                values = {
                    "amount": book_obj.total,
                    "currency": book_obj.currency_id.name,
                    "phone_number": "".join(book_obj.contact_phone.split(' - ')),
                    "name": book_obj.contact_id.name,
                    "email": book_obj.contact_email,
                    "time_limit": different_time
                }
                res = ERR.get_no_error(values)
            else:
                res = ERR.get_error(additional_message='Reservation Not Found')
        elif action == 'get_payment_acquirer_payment_gateway':
            res = self.env['payment.acquirer.number'].create_payment_acq_api(data)
        elif action == 'get_payment_acquirer_payment_gateway_frontend':
            res = self.env['payment.acquirer.number'].get_payment_acq_api(data)
        elif action == 'set_va_number':
            res = self.env['payment.acquirer.number'].set_va_number_api(data)
        elif action == 'use_pnr_quota':
            res = self.env['tt.reservation'].use_pnr_quota_api(data,context)
        elif action == 'set_sync_reservation':
            res = self.env['tt.reservation'].set_sync_reservation_api(data,context)
        else:
            raise RequestException(999)
        return res

    def set_VA(self, req):
        data = {
            'phone_number': req['number'],
            'name': req['name'],
            'email': req['email'],
            'provider': 'espay'
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'set_va', timeout=600)

    def test(self, req):
        data = {
            'phone_number': req['number'],
            'name': req['name'],
            'email': req['email'],
            'provider': 'espay'
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'test')

    def delete_VA(self, req):
        data = {
            'phone_number': req['number'],
            'provider': 'espay'
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'delete_va')

    def set_invoice(self, req):
        data = {
            'phone_number': req['number'],
            'name': req['name'],
            'email': req['email'],
            'provider': 'espay'
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'set_invoice')

    def merchant_info(self, req):
        data = {
            'phone_number': req['number'],
            'name': req['name'],
            'email': req['email'],
            'provider': 'espay'
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'merchant_info')

    def send_payment(self, req):
        request = {
            'order_number': req.get('order_number'),
            'proxy_co_uid': req.get('user_id', False),
        }
        provider = req.get('provider_type')
        action = 'issued'
        return self.send_request_to_gateway('%s/booking/%s' % (self.url, provider),
                                            request,
                                            action,
                                            timeout=180)

    def get_merchant_info(self,req):
        request = {
            'provider': req['provider'],
            'type': req['type']
        }
        action = 'merchant_info'
        return self.send_request_to_gateway('%s/payment' % (self.url),
                                            request,
                                            action,
                                            timeout=60)


    def sync_reservation_btbo_quota_pnr(self,req):
        request = {
            'carriers': req['carriers'],
            'pnr': req['pnr'],
            'pax': req['pax'],
            'provider': req['provider'],
            'provider_type': req['provider_type'],
            'order_number': req['order_number'],
            'r_n': req['r_n']
        }
        action = 'send_quota_pnr'
        return self.send_request_to_gateway('%s/booking/%s' % (self.url, req['provider_type']),
                                            request,
                                            action,
                                            timeout=60)