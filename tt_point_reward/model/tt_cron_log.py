from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

class ttCronPointRewardHandler(models.Model):
    _inherit = "tt.cron.log"

    def cron_point_reward_expired(self):
        ### BELUM UPDATE
        try:
            self.env['tt.voucher'].expire_voucher()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log("voucher expire cron")



