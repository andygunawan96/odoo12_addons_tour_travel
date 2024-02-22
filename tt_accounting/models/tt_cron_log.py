from odoo import api,models,fields
from ...tools import variables
import json
import logging,traceback
from datetime import datetime, date, timedelta
_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_expire_top_up(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                new_top_up = self.env['tt.top.up'].search([('state', 'in', ['confirm','request','expired']),('ho_id','=',ho_obj.id)])
                for top_up in new_top_up:
                    try:
                        if datetime.now() >= (top_up.due_date or datetime.min):
                            top_up.action_expired_top_up()
                    except Exception as e:
                        _logger.error('%s something failed during expired cron.\n' % (top_up.name) + traceback.format_exc())
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto-reset payment unique amount', ho_id=ho_obj.id)

    def cron_expire_refund(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                new_refund = self.env['tt.refund'].search([('state', '=', 'sent'),('ho_id','=',ho_obj.id)])
                for rec in new_refund:
                    try:
                        if datetime.now() >= rec.hold_date:
                            rec.action_expired()
                    except Exception as e:
                        _logger.error('%s something failed during expired cron.\n' % (rec.name) + traceback.format_exc())
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto-expired refund', ho_id=ho_obj.id)

    def cron_action_approve_refund(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                finalized_refunds = self.env['tt.refund'].search([('state', '=', 'final'), ('is_vendor_received', '=', True),('ho_id','=',ho_obj.id)])
                for rec in finalized_refunds:
                    try:
                        if date.today() >= rec.refund_date:
                            rec.action_approve()
                    except Exception as e:
                        _logger.error('%s something failed during refund action approve cron.\n' % (rec.name) + traceback.format_exc())
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto-action-approve refund.', ho_id=ho_obj.id)

    def sub_func_agent_balance_report_log(self):
        pass

    def cron_process_ledger_queue(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                ledger_queue_objs = self.env['tt.ledger.queue'].search([('ho_id','=',ho_obj.id),
                                                                        ('active','=',True)],limit=100)

                create_vals = []
                for ledger_queue_obj in ledger_queue_objs:
                    ledger_data = json.loads(ledger_queue_obj.ledger_values_data)
                    if type(ledger_data) == dict:
                        create_vals.append(ledger_data)
                    elif type(ledger_data) == list:
                        create_vals += ledger_data
                ledger_count = len(create_vals)
                _logger.info("##### Processing Ledger Queue for HO: %s, %s Ledgers" % (ho_obj.name,ledger_count))
                self.env['tt.ledger'].create(create_vals)

                ledger_queue_objs.write({
                    'active': False,
                    'ledger_created_date': datetime.now()
                })
                _logger.info("##### Completed Ledger Queue for HO: %s, %s Ledgers" % (ho_obj.name,ledger_count))
                self.env.cr.commit()
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto-process ledger queue', ho_id=ho_obj.id)

    def cron_ledger_statement_agent(self, create_ledger_statement=False):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                # comment for now karena bs berulang ulang
                ## problem di rodextrip sangat lama start 01.00 selesai 05.00 bahkan tdk selesai karena timeout worker cron 2400s
                if create_ledger_statement:
                    list_agent_obj = self.env['tt.agent'].search([('ho_id','=',ho_obj.id)])
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
                self.write_cron_log('auto-create ledger statement agent', ho_id=ho_obj.id)

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