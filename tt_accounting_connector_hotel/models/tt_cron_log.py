from odoo import api,models,fields
import os,traceback,pytz,logging
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class TtCronLogInhAccHotel(models.Model):
    _inherit = 'tt.cron.log'

    def cron_send_hotel_transactions_to_vendor(self):
        try:
            self.env['tt.reservation.hotel'].send_transaction_batches_to_accounting(1)
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-send hotel transactions to vendor')