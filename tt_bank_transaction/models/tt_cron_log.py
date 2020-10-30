from odoo import api,models,fields
from ...tools import variables
import logging,traceback
import re
import json,pytz
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

class ttCronTopUpValidator(models.Model):
    _inherit = 'tt.cron.log'

    def cron_auto_top_up_validator(self):
        if 3 <= datetime.now(pytz.timezone('Asia/Jakarta')).hour < 21:
            try:
                # get data from top up
                top_up_objs = self.env['tt.top.up'].sudo().search([('state', '=', 'request')])
                number_checker = re.compile("^[0-9]*$")
                for top_up_obj in top_up_objs:
                    account_number = ""
                    if top_up_obj.payment_id.acquirer_id.account_number:
                        for acc_number in top_up_obj.payment_id.acquirer_id.account_number:
                            if number_checker.match(acc_number):
                                account_number += acc_number
                    transaction = self.env['tt.bank.accounts'].search([('bank_account_number_without_dot', '=', account_number)])
                    if transaction:
                        date_exist = transaction.bank_transaction_date_ids.filtered(lambda x: x.date == datetime.today().strftime("%Y-%m-%d"))
                        if date_exist:
                            result = date_exist.transaction_ids.filtered(lambda x: x.transaction_amount == top_up_obj.total and x.transaction_type == 'C')
                            if result:
                                if result.transaction_message == '':
                                    reference_code = result.transaction_code
                                else:
                                    reference_code = result.transaction_message
                                transaction_date = result.transaction_date

                                # get payment data
                                payment_data = self.env['tt.payment'].browse(int(top_up_obj.payment_id))

                                # set value for payment data
                                payment_data.reference = reference_code
                                payment_data.payment_date = transaction_date

                                # validate payment
                                payment_data.action_validate_from_button()
                                payment_data.action_approve_from_button()

                                result.top_up_validated(top_up_obj.id)
                            else:
                                _logger.error("%s ID, is not found within transaction" % top_up_obj.id)
                                continue
                        else:
                            _logger.error("%s is not found within date inside date" % datetime.today().strftime("%Y-%m-%d"))
                            continue
                    else:
                        _logger.error("%s ID, bank not found" % top_up_obj.id)
                        continue
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto tup-up validator by system')
            #payment reservation
            try:
                top_up_objs = self.env['payment.acquirer.number'].search([('state','=','close')])
                for top_up_obj in top_up_objs:
                    transaction = self.env['tt.bank.accounts'].search([])
                    if transaction:
                        for transaction_data in transaction:
                            date_exist = transaction_data.bank_transaction_date_ids.filtered(lambda x: x.date == datetime.today().strftime("%Y-%m-%d"))
                            if date_exist:
                                result = date_exist.transaction_ids.filtered(lambda x: x.transaction_amount == top_up_obj.amount + top_up_obj.unique_amount and x.transaction_type == 'C')
                                if result:
                                    if result.transaction_message == '':
                                        reference_code = result.transaction_code
                                    else:
                                        reference_code = result.transaction_message
                                    agent_id = self.env['tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[top_up_obj['number'].split('.')[0]]].search([('name', '=', '%s.%s' %(top_up_obj['number'].split('.')[0], top_up_obj['number'].split('.')[1]))]).agent_id
                                    if not self.env['tt.payment'].search([('reference', '=', reference_code)]):
                                        # topup
                                        context = {
                                            'co_agent_id': agent_id.id,
                                            'co_uid': self.env.ref('tt_base.base_top_up_admin').id
                                        }
                                        request = {
                                            'amount': top_up_obj.amount - top_up_obj.unique_amount,
                                            'seq_id': self.env.ref('tt_base.payment_acquirer_ho_payment_gateway_bca').seq_id,
                                            'currency_code': result.currency_id.name,
                                            'payment_ref': reference_code,
                                            'payment_seq_id': self.env.ref('tt_base.payment_acquirer_ho_payment_gateway_bca').seq_id,
                                            'subsidy': top_up_obj.unique_amount
                                        }

                                        res = self.env['tt.top.up'].create_top_up_api(request, context, True)
                                        if res['error_code'] == 0:
                                            request = {
                                                'virtual_account': '',
                                                'name': res['response']['name'],
                                                'payment_ref': reference_code,
                                                'fee': 0
                                            }
                                            res = self.env['tt.top.up'].action_va_top_up(request, context)
                                            self._cr.commit()
                                            result.top_up_validated(res['response']['top_up_id'])
                                    book_obj = self.env['tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[top_up_obj['number'].split('.')[0]]].search([('name', '=', '%s.%s' % (top_up_obj['number'].split('.')[0], top_up_obj['number'].split('.')[1])), ('state', 'in', ['booked'])], limit=1)

                                    if book_obj:
                                        #login gateway, payment
                                        req = {
                                            'order_number': book_obj.name,
                                            'user_id': book_obj.user_id.id,
                                            'provider_type': variables.PROVIDER_TYPE_PREFIX[book_obj.name.split('.')[0]]
                                        }
                                        res = self.env['tt.payment.api.con'].send_payment(req)
                                        top_up_obj.state = 'done'
                                        _logger.info(json.dumps(res))
                                        #tutup payment acq number

                    else:
                        _logger.error("%s ID, is not found within transaction" % top_up_obj.id)
                        continue

            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto tup-up validator by system')

        else:
            _logger.error("Cron only works between 0300 to 2100 UTC +7")

    def cron_auto_get_bank_transaction(self):
        if 3 <= datetime.now(pytz.timezone('Asia/Jakarta')).hour < 21:
            account_objs = self.env['tt.bank.accounts'].search([('is_get_transaction','=',True)])
            for rec in account_objs:
                try:
                    # get_bank_account = self.env.ref('tt_bank_transaction.bank_account_bca_1')
                    #can be modified to respected account
                    data = {
                        'account_id': rec.id,
                        'account_number': rec.bank_account_number_without_dot,
                        'provider': rec.bank_id.code,
                        'startdate': datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d"),
                        'enddate': datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d"),
                    }
                    #called function to proceed data and input in bank transaction
                    result = self.env['tt.bank.transaction'].get_data(data)
                    self.cron_auto_top_up_validator()
                except Exception as e:
                    self.create_cron_log_folder()
                    self.write_cron_log('auto get bank transaction',rec.bank_account_number)
        else:
            _logger.error("Cron only works between 0300 AM to 2100 PM UTC+7")

    def cron_auto_proceed_bank_transaction(self):
        try:
            bank_transaction_data = self.env['tt.bank.transaction'].search([('transaction_date', '<', datetime.today()), ('transaction_process', '=', 'unprocess')])
            for i in bank_transaction_data:
                i.change_process_status()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log("auto proceed yesterday transaction data")

    def cron_auto_change_nextcall_get_bank_transaction(self,int_values=30):
        try:
            self.env.ref('tt_bank_transaction.cron_auto_get_bank_transaction').interval_number = int_values
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto change nexctcall get bank transaction')

