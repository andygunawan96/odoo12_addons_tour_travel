from odoo import api,models,fields
import os,traceback,pytz,logging
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class TtCronLogInhAccConn(models.Model):
    _inherit = 'tt.cron.log'

    def cron_send_accounting_to_vendor(self):
        try:
            queue_obj = self.env['tt.accounting.queue'].search([('state', '=', 'new')])
            for rec in queue_obj:
                rec.action_send_to_vendor()
                self.env.cr.commit()
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-send accounting data to vendor')

    def cron_send_refund_transactions_to_vendor(self):
        try:
            self.env['tt.refund'].send_transaction_batches_to_accounting(1)
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-send refund transactions to vendor')

    def cron_send_top_up_transactions_to_vendor(self):
        try:
            self.env['tt.top.up'].send_transaction_batches_to_accounting(1)
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-send top up transactions to vendor')
