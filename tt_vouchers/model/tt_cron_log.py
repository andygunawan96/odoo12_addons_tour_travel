from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

class ttCronVoucherHandler(models.Model):
    _inherit = "tt.cron.log"

    def cron_voucher_activator(self):
        try:
            voucher = self.env['tt.voucher.detail'].activate_voucher()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log("voucher activator cron")

    def cron_voucher_detail_expirator(self):
        try:
            voucher = self.env['tt.voucher.detail'].expire_detail_voucher()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log("voucher detail expire cron")

    def cron_voucher_expired(self):
        try:
            self.env['tt.voucher'].expire_voucher()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log("voucher expire cron")