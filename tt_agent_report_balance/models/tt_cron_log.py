from odoo import api,models,fields
from datetime import datetime,timedelta
import pytz

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def sub_func_agent_balance_report_log(self):
        date = datetime.now(pytz.timezone('Asia/Jakarta')) - timedelta(days=1)
        ho_list = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for rec in ho_list:
            agent_balance_wz_obj = self.env['tt.agent.report.balance.wizard'].create({
                'ho_id': rec.id,
                'all_agent': True,
                'date_from': date,
                'date_to': date,
                'logging_daily': True
            })
            log_files = agent_balance_wz_obj.action_print_excel()
            self.env['tt.agent.report.balance.log'].create({
                'file': log_files,
                'name': 'Daily Agent Report Balance Log %s.xlsx' % (date.strftime('%Y-%m-%d %H:%M:%S')),
                'date': date,
                'ho_id': rec.id
            })

    def cron_customer_parent_balance_report_log(self):
        date = datetime.now(pytz.timezone('Asia/Jakarta')) - timedelta(days=1)
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                agent_objs = self.env['tt.agent'].search([('ho_id', '=', ho_obj.id)])
                for agent_obj in agent_objs:
                    cust_par_balance_wz_obj = self.env['tt.customer.parent.report.balance.wizard'].create({
                        'ho_id': ho_obj.id,
                        'agent_id': agent_obj.id,
                        'all_agent': False,
                        'all_customer_parent': True,
                        'date_from': date,
                        'date_to': date,
                        'logging_daily': True
                    })
                    log_files = cust_par_balance_wz_obj.action_print_excel()
                    self.env['tt.customer.parent.report.balance.log'].create({
                        'file': log_files,
                        'name': 'Daily Customer Parent Report Balance Log %s.xlsx' % (date.strftime('%Y-%m-%d %H:%M:%S')),
                        'date': date,
                        'ho_id': ho_obj.id,
                        'agent_id': agent_obj.id
                    })
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto-create customer parent balance report log', ho_id=ho_obj.id)
