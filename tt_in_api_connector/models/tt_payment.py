from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException

class TtPaymentApiCon(models.Model):
    _name = 'tt.payment.api.con'
    _inherit = 'tt.api.con'

    table_name = 'payment.acquirer'

    def action_call(self, table_obj, action, data, context):

        if action == 'payment':

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
                pass
            elif self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0].state == 'close':
                #close
                provider_type = self.env['tt.provider.type'].search([])
                check = 0
                for rec in provider_type:
                    # cari nomor VA
                    res = self.env['tt.reservation.%s' % rec.code].search([
                        ('state', '=', 'booked'),
                        ('payment_method', '=', self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0].payment_acquirer_id.seq_id),
                        ('va_number', '=', data['virtual_account'])])
                    if res:
                        #payment
                        self.send_request_to_gateway('%s/booking/%s' % (self.url, rec.code), data, 'issued')
                        check = 1
                        break
                if check == 0:
                    #MUNGKIN EXPIRED TANYA ACCOUNTING
                    pass
                pass
            elif self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])[0].state == 'done':
                #close already done
                pass
            # payment_acq = self.env['payment.acquirer.number'].search([('number', '=', data['virtual_account'])])

        elif action == 'create_booking_reservation_offline_api':
            res = table_obj.create_booking_reservation_offline_api(data, context)
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
