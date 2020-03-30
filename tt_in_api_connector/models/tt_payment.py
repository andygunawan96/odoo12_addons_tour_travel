from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging
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
                    # check ada payment ref yg kembar ngga
                    if not self.env['tt.payment'].search([('reference', '=', data['payment_ref'])]):
                        # topup

                        agent_id = self.env['tt.agent'].browse(self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0].agent_id.id)
                        context = {
                            'co_agent_id': agent_id.id,
                            'co_uid': self.env.ref('tt_base.base_top_up_admin').id
                        }
                        request = {
                            'amount': data['amount'],
                            'seq_id': self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0].payment_acquirer_id.seq_id,
                            'currency_code': data['ccy'],
                            'payment_ref': data['payment_ref'],
                            'payment_seq_id': self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0].payment_acquirer_id.seq_id
                        }

                        res = self.env['tt.top.up'].create_top_up_api(request,context, True)
                        if res['error_code'] == 0:
                            request = {
                                'virtual_account': data['virtual_account'],
                                'name': res['response']['name'],
                                'payment_ref': data['payment_ref'],
                            }
                            res = self.env['tt.top.up'].action_va_top_up(request, context)
                    else:
                        res = ERR.get_error(500, additional_message="double payment")
                else:
                    res = ERR.get_error(500, additional_message="VA Not Found")
            elif data['va_type'] == 'close':
                res = ''
                agent_id = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])]).agent_id
                if not self.env['tt.payment'].search([('reference', '=', data['payment_ref'])]):
                    # topup
                    context = {
                        'co_agent_id': agent_id.id,
                        'co_uid': self.env.ref('tt_base.base_top_up_admin').id
                    }
                    request = {
                        'amount': data['amount'],
                        'seq_id': self.env.ref('tt_base.payment_acquirer_ho_payment_gateway').seq_id,
                        'currency_code': data['ccy'],
                        'payment_ref': data['payment_ref'],
                        'payment_seq_id': self.env.ref('tt_base.payment_acquirer_ho_payment_gateway').seq_id
                    }

                    res = self.env['tt.top.up'].create_top_up_api(request,context, True)
                    if res['error_code'] == 0:
                        request = {
                            'virtual_account': data['virtual_account'],
                            'name': res['response']['name'],
                            'payment_ref': data['payment_ref'],
                        }
                        res = self.env['tt.top.up'].action_va_top_up(request, context)

                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number']), ('state', 'in', ['booked'])])
                _logger.info(json.dumps(book_obj))
                if book_obj:
                    values = {
                        "amount": book_obj.total,
                        "currency": book_obj.currency_id.name,
                        "co_uid": book_obj.booked_uid.id
                    }
                    res = ERR.get_no_error(values)
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
                values = {
                    "amount": book_obj.total,
                    "currency": book_obj.currency_id.name
                }
                res = ERR.get_no_error(values)
            else:
                res = ERR.get_error(additional_message='Reservation Not Found')
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
        return self.send_request_to_gateway('%s/payment' % (self.url), data, 'set_va')

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
