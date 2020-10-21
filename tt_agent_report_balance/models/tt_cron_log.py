from odoo import api,models,fields
from datetime import datetime,timedelta
import pytz

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def sub_func_agent_balance_report_log(self):
        agent_balance_wz_obj = self.env['tt.agent.report.balance.wizard'].create({
            'all_agent': True,
            'date_from': datetime.now(pytz.timezone('Asia/Jakarta')) - timedelta(days=1),
            'date_to': datetime.now(pytz.timezone('Asia/Jakarta')) - timedelta(days=1),
            'logging_daily': True
        })
        log_files = agent_balance_wz_obj.action_print_excel()
        self.env['tt.agent.report.balance.log'].create({
            'file': log_files
        })