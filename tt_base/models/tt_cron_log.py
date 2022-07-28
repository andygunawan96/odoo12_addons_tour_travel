from odoo import api,models,fields
import os,traceback,pytz,logging
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class TtCronLog(models.Model):
    _name = 'tt.cron.log'
    _description = 'Base Cron Log Model'

    ##run only once
    def create_cron_log_folder(self):
        dest = '/var/log/odoo/cron_log'
        if not os.path.exists(dest):
            os.mkdir(dest)

    def write_cron_log(self,action_name,additional_message=''):
        _logger.error(traceback.format_exc())
        file = open('%s/%s_%s_error.log' % (
            '/var/log/odoo/cron_log',action_name, datetime.now().strftime('%Y-%m-%d_%H:%M:%S')),
                    'w')
        file.write(traceback.format_exc()+"\n"+additional_message)
        file.close()
        try:
            self.env['tt.api.con'].send_cron_error_notification(action_name)
        except Exception as e:
            _logger.error("Send Cron Error Notification Telegram Error")

    def cron_reset_payment_unique_amount(self):
        try:
            seq = self.env['ir.sequence'].search([('code','=','tt.payment.unique.amount')])
            seq.number_next_actual = 100
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-reset payment unique amount')

    def cron_delete_expired_file(self):
        try:
            files = self.env['tt.upload.center'].with_context({'active_test':False}).search([('will_be_deleted_time', '<=', datetime.now())])
            for rec in files:
                rec.unlink()
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-delete expired file')

    def cron_unban_users(self):
        try:
            banned_users_obj = self.env['tt.ban.user'].search([('end_datetime','<', datetime.now())])
            for rec in banned_users_obj:
                rec.user_id.is_banned = False
                rec.active = False
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-unban users')

    def cron_expire_quota(self):
        try:
            pnr_quota_obj = self.env['tt.pnr.quota'].search([('expired_date','<', datetime.now(pytz.timezone('Asia/Jakarta')).date()), ('state','=','active')])
            # pnr_quota_obj = self.env['tt.pnr.quota'].search([('expired_date','<=', datetime.now(pytz.timezone('Asia/Jakarta')).date()), ('state','=','active')]) #testing
            for rec in pnr_quota_obj:
                rec.state = 'waiting'
                rec.amount = rec.price_package_id.minimum_fee
                rec.calc_amount_internal()
                rec.calc_amount_external()
                rec.calc_amount_total()
            self.env.cr.commit()
            agent_obj = self.env['tt.agent'].search([('is_using_pnr_quota', '=', True), ('quota_total_duration', '=', False)])
            for rec in agent_obj:
                res = self.env['tt.pnr.quota'].create_pnr_quota_api(
                    {
                        'quota_seq_id': rec.quota_package_id.seq_id
                    },
                    {
                        'co_agent_id': rec.id
                    }
                )
                if res['error_code'] != 0:
                    rec.ban_user_api()
                    _logger.info(res['error_msg'])
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            self.create_cron_log_folder()
            self.write_cron_log('auto-expire quota pnr')

    def cron_payment_pnr_quota(self):
        try:
            pnr_quota_obj = self.env['tt.pnr.quota'].search([('state', '=', 'waiting')])
            for rec in pnr_quota_obj:
                rec.payment_pnr_quota_api()
                if rec.state != 'done':
                    rec.agent_id.ban_user_api()
                    rec.state = 'failed'
        except Exception as e:
            _logger.error(traceback.format_exc())
            self.create_cron_log_folder()
            self.write_cron_log('auto-payment quota pnr')

    def cron_send_email_queue(self):
        try:
            queue_obj = self.env['tt.email.queue'].search([])
            for rec in queue_obj:
                rec.action_send_email()
                self.env.cr.commit()
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-send email queue')

    def cron_expire_unique_amount(self):
        try:
            unique_obj = self.env['unique.amount'].search([('create_date','<',datetime.now() - timedelta(days=3))])
            for rec in unique_obj:
                rec.active = False
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-expired unique amount')

    def cron_expire_payment_acq_number(self):
        try:
            payment_acq = self.env['payment.acquirer.number'].search([('state', '=', 'close'), '|', ('create_date','<',datetime.now() - timedelta(hours=1)), ('time_limit','<',datetime.now())])
            for rec in payment_acq:
                rec.state = 'cancel'
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-expired payment acquirer number')


    def cron_point_reward_statement_agent(self):
        try:
            # comment for now karena bs berulang ulang
            list_agent_obj = self.env['tt.agent'].search([])
            for agent_obj in list_agent_obj:
                try:
                    agent_obj.create_point_reward_statement()
                    _logger.info("Point Reward Statement Success for %s %s" % (agent_obj.id, agent_obj.name))
                    self._cr.commit()
                except Exception as e:
                    _logger.error("Failed Point Reward Statement for %s\n%s" % (agent_obj.name,str(e)))
            # self.sub_func_agent_balance_report_log()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-create point reward statement agent')

