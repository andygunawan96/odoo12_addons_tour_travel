from odoo import api,models,fields
import os,traceback,pytz,logging
from datetime import datetime,date

_logger = logging.getLogger(__name__)

class TtCronLog(models.Model):
    _name = 'tt.cron.log'
    _description = 'Base Cron Log Model'

    ##run only once
    def create_cron_log_folder(self):
        dest = '/var/log/odoo/cron_log'
        if not os.path.exists(dest):
            os.mkdir(dest)

    def write_cron_log(self,action_name):
        file = open('%s/%s_%s_error.log' % (
            '/var/log/odoo/cron_log',action_name, datetime.now().strftime('%Y-%m-%d_%H:%M:%S')),
                    'w')
        file.write(traceback.format_exc())
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
            pnr_quota_obj = self.env['tt.pnr.quota'].search([('expired_date','<', datetime.now(pytz.timezone('Asia/Jakarta')).date())])
            for rec in pnr_quota_obj:
                rec.is_expired = True
        except:
            self.create_cron_log_folder()
            self.write_cron_log('auto-expire quota')

    # def cron_extend_quota(self):
    #     ##auto extend quota jika ada saldo
    #     try:
    #
    #     except:

