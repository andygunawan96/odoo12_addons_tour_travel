from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging
from datetime import datetime, timedelta
import traceback
_logger = logging.getLogger(__name__)

class TtPaymentApiCon(models.Model):
    _name = 'tt.payment.api.con'
    _inherit = 'tt.api.con'

    table_name = 'payment.acquirer'

    def action_call(self, table_obj, action, data, context):
        if action == 'payment':
            if data['va_type'] == 'open':
                _logger.info("##############STARTING ESPAY OPEN TOP UP##############")
                payment_acq_number_obj = self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])], limit=1)
                if payment_acq_number_obj.state == 'open':
                    # check ada payment ref yg kembar ngga
                    if not self.env['tt.payment'].search([('reference', '=', data['payment_ref'])]):
                        # topup
                        if payment_acq_number_obj.payment_acquirer_id.minimum_amount > payment_acq_number_obj.payment_acquirer_id.va_fee:
                            fee_amount = payment_acq_number_obj.payment_acquirer_id.minimum_amount
                        else:
                            fee_amount = payment_acq_number_obj.payment_acquirer_id.va_fee
                        agent_id = self.env['tt.agent'].browse(payment_acq_number_obj.agent_id.id)
                        context = {
                            'co_agent_id': agent_id.id,
                            'co_uid': self.env.user.id
                            # 'co_uid': self.env.ref('base.user_root').id
                        }
                        request = {
                            'amount': data['amount'],
                            'seq_id': payment_acq_number_obj.payment_acquirer_id.seq_id,
                            'currency_code': data['ccy'],
                            'payment_ref': data['payment_ref'],
                            'payment_seq_id': payment_acq_number_obj.payment_acquirer_id.seq_id,
                            'fee': fee_amount
                        }

                        res = self.env['tt.top.up'].create_top_up_api(request,context, True)
                        if res['error_code'] == 0:
                            request = {
                                'virtual_account': data['virtual_account'],
                                'name': res['response']['name'],
                                'payment_ref': data['payment_ref'],
                                'fee': fee_amount
                            }
                            res = self.env['tt.top.up'].action_va_top_up(request, context, payment_acq_number_obj.id)
                            _logger.info("##############SUCCESS ESPAY OPEN TOP UP##############")
                    else:
                        res = ERR.get_error(500, additional_message="double payment")
                        _logger.info("##############ERROR ESPAY OPEN TOP UP##############")
                else:
                    res = ERR.get_error(500, additional_message="VA Not Found")
                    _logger.info("##############ERROR ESPAY OPEN TOP UP##############")
                _logger.info("##############END ESPAY OPEN TOP UP##############")
            elif data['va_type'] == 'close':
                try:
                    res = ''
                    #ganti ke done
                    _logger.info("##############STARTING ESPAY CLOSED PAYMENT##############")
                    pay_acq_num = self.env['payment.acquirer.number'].search([('number', 'ilike', data['order_number']), ('state','=','close')])
                    if pay_acq_num:
                        ## CLOSE PAYMENT
                        _logger.info("### FOUND PAY ACQ NUM %s ###" % (str(pay_acq_num.ids)))
                        _logger.info("USED PAY ACQ %s, State %s, Fee Amount %s" % (pay_acq_num[len(pay_acq_num)-1].id,pay_acq_num[len(pay_acq_num)-1].state, pay_acq_num[len(pay_acq_num)-1].fee_amount))
                        # pay_acq_num[len(pay_acq_num)-1].fee_amount = float(data['fee'])
                        _logger.info("UPDATING PAY ACQ NUM TO state %s and fee %s" % (pay_acq_num[len(pay_acq_num)-1].state,pay_acq_num[len(pay_acq_num)-1].fee_amount))

                        if data['provider_type'] != 'top.up':
                            ## TOP UP
                            agent_id = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])]).agent_id
                            if not self.env['tt.payment'].search([('reference', '=', data['payment_ref'])]):
                                # topup
                                context = {
                                    'co_agent_id': agent_id.id,
                                    'co_uid': self.env.ref('base.user_root').id
                                }
                                request = {
                                    'amount': data['amount'],
                                    'currency_code': data['ccy'],
                                    'payment_ref': data['payment_ref'],
                                    'payment_seq_id': pay_acq_num[len(pay_acq_num)-1].payment_acquirer_id.seq_id,
                                    'fee': pay_acq_num.fee_amount
                                }

                                res = self.env['tt.top.up'].create_top_up_api(request,context, True)
                                if res['error_code'] == 0:
                                    request = {
                                        'virtual_account': data['virtual_account'],
                                        'name': res['response']['name'],
                                        'payment_ref': data['payment_ref'],
                                        # 'fee': data['fee']
                                        'fee': pay_acq_num.fee_amount
                                    }
                                    res = self.env['tt.top.up'].action_va_top_up(request, context, pay_acq_num[len(pay_acq_num)-1].id)
                                    pay_acq_num[len(pay_acq_num) - 1].state = 'process'

                    if data['provider_type'] != 'top.up':
                        ## RESERVASI
                        book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number']), ('state', 'in', ['booked','halt_booked'])], limit=1)
                        _logger.info(data['order_number'])
                        if book_obj:
                            pay_acq_num = self.env['payment.acquirer.number'].search([('number', 'ilike', data['order_number']), ('state', 'in', ['close', 'process','waiting','done'])],limit=1) ## SELECT ULANG KARENA BISA CONCURRENT, UNTUK AMBIL FEE AMOUNT
                            reservation_transaction_amount = book_obj.total - book_obj.total_discount
                            if pay_acq_num:
                                reservation_transaction_amount += pay_acq_num.fee_amount
                            website_use_point_reward = self.env['ir.config_parameter'].sudo().get_param('use_point_reward')
                            if website_use_point_reward == 'True':
                                if pay_acq_num.is_using_point_reward:
                                    reservation_transaction_amount -= pay_acq_num.point_reward_amount
                            ##testing dulu
                            # if reservation_transaction_amount == float(data['transaction_amount']):
                            if reservation_transaction_amount == float(data['amount']):
                                seq_id = ''
                                if book_obj.payment_acquirer_number_id:
                                    seq_id = book_obj.payment_acquirer_number_id.payment_acquirer_id.seq_id
                                values = {
                                    "amount": book_obj.total - book_obj.total_discount,
                                    "currency": book_obj.currency_id.name,
                                    "co_uid": book_obj.user_id.id,
                                    "is_btc": True if book_obj.agent_type_id.code == 'btc' else False,
                                    'member': False, # KALAU BAYAR PAKE ESPAY PASTI MEMBER FALSE
                                    'acquirer_seq_id': seq_id,
                                    'force_issued': True,
                                    'use_point': book_obj.is_using_point_reward
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
                    else:
                        pay_acq_num = self.env['payment.acquirer.number'].search([('number', 'ilike', data['order_number']), ('state', 'in', ['close', 'waiting', 'done'])],limit=1)  ## SELECT ULANG KARENA BISA CONCURRENT, UNTUK AMBIL FEE AMOUNT
                        if pay_acq_num:
                            pay_acq_num.state = 'done'
                            request = {
                                'virtual_account': data['virtual_account'],
                                'name': data['order_number'],
                                'payment_ref': data['payment_ref'],
                                'fee': pay_acq_num.fee_amount
                            }
                            self.env['tt.top.up'].action_va_top_up(request, context,pay_acq_num[len(pay_acq_num) - 1].id)
                            res = ERR.get_no_error()
                        else:
                            res = ERR.get_error(500, additional_message="PAYMENT NOT FOUND")

                except Exception as e:
                    _logger.error(traceback.format_exc())
                    raise e
                _logger.info("##############ENDING ESPAY CLOSED PAYMENT##############")
            elif self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0].state == 'done':
                #close already done
                pass
            # payment_acq = self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])
        elif action == 'get_amount':
            if data['provider_type'] != 'top.up':
                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number']), ('state', 'in', ['booked','halt_booked']), ('ho_id','=', context['co_ho_id'])])
                if book_obj:
                    amount = book_obj.total - book_obj.total_discount
                    phone_number = "".join(book_obj.contact_phone.split(' - '))
                    currency = book_obj.currency_id.name
                    name = book_obj.contact_id.name
                    email = book_obj.contact_email

            else:
                book_obj = self.env['tt.%s' % data['provider_type']].search([('name', '=', data['order_number']), ('state', 'in', ['confirm', 'request']), ('ho_id','=', context['co_ho_id'])])
                if book_obj:
                    amount = book_obj.total_with_fees ## karena harga amount + fees * 2 agar sama dengan frontend
                    for phone_obj in book_obj.agent_id.phone_ids:
                        if phone_obj.phone_number:
                            phone_number = phone_obj.phone_number
                            break
                    currency = book_obj.currency_id.name
                    name = book_obj.request_uid.name
                    email = book_obj.request_uid.email
            if book_obj:
                payment_acq_number_obj = self.env['payment.acquirer.number'].search([('number', '=', data['payment_acq_number']), ('ho_id','=', context['co_ho_id'])])
                if payment_acq_number_obj:
                    amount += payment_acq_number_obj.fee_amount
                    different_time = payment_acq_number_obj.time_limit - datetime.now()
                    timelimit = int(different_time.seconds / 60)
                    ## ada 2 cara amount langsung pakai amount di payment acq number / amount dari book_obj di kurang dengan point reward yg di pakai
                    website_use_point_reward = self.env['ir.config_parameter'].sudo().get_param('use_point_reward')
                    if website_use_point_reward == 'True':
                        if payment_acq_number_obj.is_using_point_reward:
                            amount -= payment_acq_number_obj.point_reward_amount
                # else: ## KALAU PAYMENT ACQ NUMBER TIDAK KETEMU
                #     different_time = book_obj.hold_date - datetime.now()
                #     if different_time > timedelta(hours=1): ## LEBIH DARI 1 JAM TIMELIMIT 55 MENIT
                #         timelimit = 55
                #     else: ## KURANG DARI 1 JAM, TIMELIMIT = HOLD DATE - 5 MENIT
                #         different_time_in_minutes = int(different_time.seconds / 60)
                #         timelimit = different_time_in_minutes - 5
                    values = {
                        "amount": amount,
                        "currency": currency,
                        "phone_number": phone_number,
                        "name": name,
                        "email": email,
                        "time_limit": timelimit,
                        'time_limit_datetime': payment_acq_number_obj.time_limit.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    res = ERR.get_no_error(values)
                else:
                    res = ERR.get_error(additional_message='Payment Acquirer Number not found')
            else:
                res = ERR.get_error(additional_message='Reservation Not Found')
        elif action == 'top_up': ##b2c auto top up different price
            _logger.info("##############STARTING AUTO TOP UP B2C CLOSED PAYMENT##############")
            pay_acq_num = self.env['payment.acquirer.number'].search([('number', 'ilike', data['order_number']), ('state', 'in', ['close','done']), ('ho_id','=', context['co_ho_id'])])
            agent_id = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])]).agent_id
            if not self.env['tt.payment'].search([('reference', '=', data['payment_ref'])]) and pay_acq_num and agent_id:
                # topup
                context = {
                    'co_agent_id': agent_id.id,
                    'co_uid': self.env.ref('base.user_root').id
                }
                request = {
                    'amount': data['amount'],
                    'currency_code': data['ccy'],
                    'payment_ref': data['payment_ref'],
                    'payment_seq_id': pay_acq_num[len(pay_acq_num) - 1].payment_acquirer_id.seq_id,
                    'fee': data['fee']
                }

                res = self.env['tt.top.up'].create_top_up_api(request, context, True)
                if res['error_code'] == 0:
                    request = {
                        'virtual_account': data['virtual_account'],
                        'name': res['response']['name'],
                        'payment_ref': data['payment_ref'],
                        'fee': data['fee']
                    }
                    res = self.env['tt.top.up'].action_va_top_up(request, context, pay_acq_num[len(pay_acq_num) - 1].id)
                _logger.info("##############DONE AUTO TOP UP B2C CLOSED PAYMENT##############")
                return ERR.get_no_error(res)
            _logger.info("##############ERROR AUTO TOP UP B2C CLOSED PAYMENT##############")
            return ERR.get_error(500)
        elif action == 'get_payment_acquirer_payment_gateway':
            res = self.env['payment.acquirer.number'].create_payment_acq_api(data, context)
        elif action == 'get_payment_acquirer_payment_gateway_frontend':
            res = self.env['payment.acquirer.number'].get_payment_acq_api(data, context)
        elif action == 'set_va_number':
            res = self.env['payment.acquirer.number'].set_va_number_api(data, context)
        elif action == 'set_va_number_fail':
            res = self.env['payment.acquirer.number'].set_va_number_fail_api(data, context)
        elif action == 'use_pnr_quota':
            res = self.env['tt.reservation'].use_pnr_quota_api(data,context)
        elif action == 'set_sync_reservation':
            res = self.env['tt.reservation'].set_sync_reservation_api(data,context)
        elif action == 'update_payment_acq_number':
            res = self.env['payment.acquirer.number'].update_payment_acq_number(data,context)
        else:
            raise RequestException(999)
        return res

    def set_VA(self, req, ho_id):
        data = {
            'phone_number': req['number'],
            'name': req['name'],
            'email': req['email'],
            'bank_code_list': req['bank_code_list'],
            'provider': req['provider'],
            'currency': req['currency']
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'set_va', timeout=600, ho_id=ho_id)

    def test(self, req, ho_id):
        data = {
            'phone_number': req['number'],
            'name': req['name'],
            'email': req['email'],
            'provider': 'espay'
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'test', ho_id=ho_id)

    def delete_VA(self, req, ho_id):
        data = {
            'phone_number': req['number'],
            'provider': req['provider'],
            'email': req['email'],
            'name': req['name'],
            'bank_code_list': req['bank_code_list'],
            'currency': req['currency']
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'delete_va', ho_id=ho_id)

    def set_invoice(self, req, ho_id):
        data = {
            'phone_number': req['number'],
            'name': req['name'],
            'email': req['email'],
            'provider': 'espay'
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'set_invoice', ho_id=ho_id)

    def merchant_info(self, req, ho_id):
        data = {
            'phone_number': req['number'],
            'name': req['name'],
            'email': req['email'],
            'provider': 'espay'
        }
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'merchant_info', ho_id=ho_id)

    def send_payment(self, req):
        request = {
            'order_number': req.get('order_number'),
            'proxy_co_uid': req.get('user_id', False),
            'member': req['member'],
            'force_issued': req['force_issued'],
            'acquirer_seq_id': req['acquirer_seq_id'],
            'use_point': req['use_point']
        }
        provider = req.get('provider_type')
        action = 'issued'
        return self.send_request_to_gateway('%s/booking/%s' % (self.url, provider),
                                            request,
                                            action,
                                            timeout=180, ho_id=req['ho_id'])

    def get_merchant_info(self,req, ho_id):
        request = {
            'provider': req['provider'],
            'type': req['type'],
        }
        action = 'merchant_info'
        return self.send_request_to_gateway('%s/payment' % (self.url),
                                            request,
                                            action,
                                            timeout=60, ho_id=ho_id)


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
                                            timeout=60, ho_id=req['ho_id'])