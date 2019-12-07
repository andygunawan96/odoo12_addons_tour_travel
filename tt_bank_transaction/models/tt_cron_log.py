from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

class ttCronTopUpValidator(models.Model):
    _inherit = 'tt.cron.log'

    def cron_auto_top_up_validator(self):
        try:
            # get data from top up
            data = self.env['tt.top.up'].sudo().search([('state', '=', 'request')])
            try:
                date = self.env['tt.bank.transaction.date'].search([('date', '=', datetime.today().strftime("%Y-%m-%d"))])
            except:
                raise Exception("Date haven't been created, please run get bank cron first then try validate again")
            transaction = self.env['tt.bank.transaction'].sudo().search([('bank_transaction_date_id', '=', date.id), ('transaction_process', '=', 'unprocess'), ('transaction_type', '=', 'C')])

            # check if there's an exact number
            for i in data:
                for j in transaction:
                    if i.total == j.get_transaction_amount():
                        # get payment data
                        payment_data = self.env['tt.payment'].browse(int(i.payment_id))

                        #set value for payment data
                        payment_data.reference = j.transaction_code
                        payment_data.payment_date = j.transaction_date

                        #validate payment
                        payment_data.action_validate_from_button()
                        payment_data.action_approve_from_button()

                        #connecting transaction data with respected payment
                        # i.action_validate_top_up(j.get_transaction_amount())
                        j.top_up_validated(i.id)

                        #break inside loop, continue to next data
                        break

        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto tup-up validator by system')

    def cron_auto_get_bank_transaction(self):
        try:
            get_bank_account = self.env.ref('tt_bank_transaction.bank_account_bca_1')
            #can be modified to respected account
            data = {
                'account_number': get_bank_account.bank_account_number_without_dot,
                'provider': get_bank_account.bank_id.code,
                'startdate': (datetime.today() + timedelta(hours=7)).strftime("%Y-%m-%d"),
                'enddate': (datetime.today() + timedelta(hours=7)).strftime("%Y-%m-%d"),
            }
                #called function to proceed data and input in bank transaction
            result = self.env['tt.bank.transaction'].get_data(data)

        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto get bank transaction')

    def cron_auto_proceed_bank_transaction(self):
        try:
            bank_transaction_data = self.env['tt.bank.transaction'].search([('transaction_date', '<', datetime.today()), ('transaction_process', '=', 'unprocess')])
            for i in bank_transaction_data:
                i.change_process_status()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log("auto proceed yesterday transaction data")