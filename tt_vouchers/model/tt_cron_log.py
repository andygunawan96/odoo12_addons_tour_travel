from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

class ttCronVoucherHandler(models.Model):
    _inherit = "tt.cron.log"

    def cron_voucher_activator(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                voucher = self.env['tt.voucher.detail'].activate_voucher(ho_obj.id)
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log("voucher activator cron", ho_id=ho_obj.id)

    def cron_voucher_detail_expirator(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                voucher = self.env['tt.voucher.detail'].expire_detail_voucher(ho_obj.id)
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log("voucher detail expire cron", ho_id=ho_obj.id)

    def cron_voucher_expired(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                self.env['tt.voucher'].expire_voucher(ho_obj.id)
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log("voucher expire cron", ho_id=ho_obj.id)