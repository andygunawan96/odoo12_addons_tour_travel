from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

class ttCronTopUpValidator(models.Model):
    _inherit = 'tt.cron.log'

    def cron_auto_top_up_validator(self):
        try:
            # get data from top up
            data = self.env['tt.top.up'].sudo().search([('state', '=', 'request')])
            transaction = self.env['tt.bank.transaction'].sudo().search([('transaction_process', '=', 'unprocess'), ('transaction_type', '=', 'C')])

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

            #can be modified to respected account
            data = {
                'account_number': 5110150000,
                'provider': 'bca',
                'startdate': datetime.today().strftime("%Y-%m-%d"),
                'enddate': datetime.today().strftime("%Y-%m-%d"),
            }
            try:
                #called function to proceed data and input in bank transaction
                result = self.env['tt.bank.transaction'].get_data(data)
            except Exception as e:
                result = "Failed to get data"
                _logger.error(
                    '%s something failed during expired cron.\n' % traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto get bank transaction')