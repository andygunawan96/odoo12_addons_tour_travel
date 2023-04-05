from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, date, timedelta
_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_expire_top_up(self):
        try:
            new_top_up = self.env['tt.top.up'].search([('state', 'in', ['confirm','request','expired']),])
            for top_up in new_top_up:
                try:
                    if datetime.now() >= (top_up.due_date or datetime.min):
                        top_up.action_expired_top_up()
                except Exception as e:
                    _logger.error('%s something failed during expired cron.\n' % (top_up.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-reset payment unique amount')

    def cron_expire_refund(self):
        try:
            new_refund = self.env['tt.refund'].search([('state', '=', 'sent')])
            for rec in new_refund:
                try:
                    if datetime.now() >= rec.hold_date:
                        rec.action_expired()
                except Exception as e:
                    _logger.error('%s something failed during expired cron.\n' % (rec.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-expired refund')

    def cron_action_approve_refund(self):
        try:
            finalized_refunds = self.env['tt.refund'].search([('state', '=', 'final'), ('is_vendor_received', '=', True)])
            for rec in finalized_refunds:
                try:
                    if date.today() >= rec.refund_date:
                        rec.action_approve()
                except Exception as e:
                    _logger.error('%s something failed during refund action approve cron.\n' % (rec.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-action-approve refund.')

    def sub_func_agent_balance_report_log(self):
        pass

    def cron_ledger_statement_agent(self, create_ledger_statement=False):
        try:
            # comment for now karena bs berulang ulang
            ## problem di rodextrip sangat lama start 01.00 selesai 05.00 bahkan tdk selesai karena timeout worker cron 2400s
            if create_ledger_statement:
                list_agent_obj = self.env['tt.agent'].search([])
                for agent_obj in list_agent_obj:
                    try:
                        agent_obj.create_ledger_statement()
                        _logger.info("Ledger Statement Success for %s %s" % (agent_obj.id, agent_obj.name))
                        self._cr.commit()
                    except Exception as e:
                        _logger.error("Failed Ledger Statement for %s\n%s" %(agent_obj.name,str(e)))
            self.sub_func_agent_balance_report_log()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-create ledger statement agent')

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