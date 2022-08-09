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

    # MASIH BUG KALAU ACTIVE BALANCE TIAP AGENT BISA KEMBAR KALO SKRG UNTUK FIX ADJUSTMENT 0 KEMBALI KE SALDO AWAL
    # def cron_point_reward_statement_agent(self):
    #     try:
    #         # comment for now karena bs berulang ulang
    #         list_agent_obj = self.env['tt.agent'].search([])
    #         for agent_obj in list_agent_obj:
    #             try:
    #                 agent_obj.create_point_reward_statement()
    #                 _logger.info("Point Reward Statement Success for %s %s" % (agent_obj.id, agent_obj.name))
    #                 self._cr.commit()
    #             except Exception as e:
    #                 _logger.error("Failed Point Reward Statement for %s\n%s" % (agent_obj.name,str(e)))
    #         # self.sub_func_agent_balance_report_log()
    #     except Exception as e:
    #         self.create_cron_log_folder()
    #         self.write_cron_log('auto-create point reward statement agent')


