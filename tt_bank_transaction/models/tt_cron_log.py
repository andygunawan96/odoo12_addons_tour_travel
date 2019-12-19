from odoo import api,models,fields
from ...tools import variables
import logging,traceback
import re
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

class ttCronTopUpValidator(models.Model):
    _inherit = 'tt.cron.log'

    def cron_auto_top_up_validator(self):
        if 1 < datetime.today().hour < 13:
            try:
                # get data from top up
                data = self.env['tt.top.up'].sudo().search([('state', '=', 'request')])
                number_checker = re.compile("^[0-9]*$")
                for i in data:
                    account_number = ""
                    for j in i.payment_id.acquirer_id.account_number:
                        if number_checker.match(j):
                            account_number += j
                    transaction = self.env['tt.bank.accounts'].search([('bank_account_number_without_dot', '=', account_number)])
                    if transaction:
                        date_exist = transaction.bank_transaction_date_ids.filtered(lambda x: x.date == datetime.today().strftime("%Y-%m-%d"))
                        if date_exist:
                            result = date_exist.transaction_ids.filtered(lambda x: x.transaction_amount == i.total and x.transaction_type == 'C')
                            if result:
                                if result.transaction_message == '':
                                    reference_code = result.transaction_code
                                else:
                                    reference_code = result.transaction_message
                                transaction_date = result.transaction_date

                                # get payment data
                                payment_data = self.env['tt.payment'].browse(int(i.payment_id))

                                # set value for payment data
                                payment_data.reference = reference_code
                                payment_data.payment_date = transaction_date

                                # validate payment
                                payment_data.action_validate_from_button()
                                payment_data.action_approve_from_button()

                                result.top_up_validated(i.id)
                            else:
                                _logger.error("%s ID, is not found within transaction" % i.id)
                                continue
                        else:
                            _logger.error("%s is not found within date inside date" % datetime.today().strftime("%Y-%m-%d"))
                            continue
                    else:
                        _logger.error("%s ID, bank not found" % i.id)
                        continue
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto tup-up validator by system')
        else:
            _logger.error("Cron only works between 0800 to 2000 UTC +7")

    def cron_auto_get_bank_transaction(self):
        if 1 < datetime.today().hour < 13:
            try:
                get_bank_account = self.env.ref('tt_bank_transaction.bank_account_bca_1')
                #can be modified to respected account
                data = {
                    'account_id': get_bank_account.id,
                    'account_number': get_bank_account.bank_account_number_without_dot,
                    'provider': get_bank_account.bank_id.code,
                    'startdate': (datetime.today() + timedelta(hours=7)).strftime("%Y-%m-%d"),
                    'enddate': (datetime.today() + timedelta(hours=7)).strftime("%Y-%m-%d"),
                }
                    #called function to proceed data and input in bank transaction
                result = self.env['tt.bank.transaction'].get_data(data)
                self.cron_auto_top_up_validator()
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto get bank transaction')
        else:
            _logger.error("Cron only works between 0800 AM to 0800 PM UTC+7")

    def cron_auto_proceed_bank_transaction(self):
        try:
            bank_transaction_data = self.env['tt.bank.transaction'].search([('transaction_date', '<', datetime.today()), ('transaction_process', '=', 'unprocess')])
            for i in bank_transaction_data:
                i.change_process_status()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log("auto proceed yesterday transaction data")