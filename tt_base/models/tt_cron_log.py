from odoo import api,models,fields
import os,traceback,pytz,logging
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from ...tools import util

_logger = logging.getLogger(__name__)

class TtCronLog(models.Model):
    _name = 'tt.cron.log'
    _description = 'Base Cron Log Model'

    ##run only once
    def create_cron_log_folder(self):
        dest = '/var/log/odoo/cron_log'
        if not os.path.exists(dest):
            os.mkdir(dest)

    def write_cron_log(self,action_name,additional_message='',ho_id=''):
        _logger.error(traceback.format_exc())
        file = open('%s/%s_%s_error.log' % ('/var/log/odoo/cron_log',action_name, datetime.now().strftime('%Y-%m-%d_%H:%M:%S')), 'w')
        file.write(traceback.format_exc()+"\n"+additional_message)
        file.close()
        try:
            ## tambah context
            ## kurang test
            self.env['tt.api.con'].send_cron_error_notification(action_name, ho_id)
        except Exception as e:
            _logger.error("Send Cron Error Notification Telegram Error")

    def cron_reset_payment_unique_amount(self):
        try:
            seq = self.env['ir.sequence'].search([('code','=','tt.payment.unique.amount')])
            seq.number_next_actual = 100
        except Exception as e:
            ## tidak tahu pakai context apa
            self.create_cron_log_folder()
            self.write_cron_log('auto-reset payment unique amount')

    def cron_delete_expired_file(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                files = self.env['tt.upload.center'].with_context({'active_test':False}).search([('will_be_deleted_time', '<=', datetime.now()),('ho_id','=', ho_obj.id)])
                idx_commit_count = 0
                for rec in files:
                    rec.unlink()

                    #commit tiap 200 biar aman dari timeout jika terjadi
                    idx_commit_count += 1
                    if idx_commit_count >= 200:
                        self.env.cr.commit()
                        idx_commit_count = 0
            except:
                self.create_cron_log_folder()
                self.write_cron_log('auto-delete expired file', ho_id=ho_obj.id)

    def cron_unban_users(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                banned_users_obj = self.env['tt.ban.user'].search([('end_datetime','<', datetime.now()), ('ho_id','=',ho_obj.id)])
                for rec in banned_users_obj:
                    rec.user_id.is_banned = False
                    rec.active = False
            except:
                self.create_cron_log_folder()
                self.write_cron_log('auto-unban users', ho_id=ho_obj.id)

    def cron_expire_quota(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                pnr_quota_obj = self.env['tt.pnr.quota'].search([('expired_date','<', datetime.now(pytz.timezone('Asia/Jakarta')).date()), ('state','=','active'), ('ho_id','=',ho_obj.id)])
                # pnr_quota_obj = self.env['tt.pnr.quota'].search([('expired_date','<=', datetime.now(pytz.timezone('Asia/Jakarta')).date()), ('state','=','active')]) #testing
                for rec in pnr_quota_obj:
                    rec.state = 'waiting'
                    rec.amount = rec.price_package_id.minimum_fee
                    rec.calc_amount_internal()
                    rec.calc_amount_external()
                    rec.calc_amount_total()

                    ## CREATE EMAIL QUEUE
                    temp_data = {
                        'provider_type': 'quota_pnr',
                        'order_number': rec.name,
                    }
                    temp_context = {
                        'co_agent_id': rec.agent_id.id
                    }
                    self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)

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
                self.write_cron_log('auto-expire quota pnr', ho_id=ho_obj.id)

    def cron_payment_pnr_quota(self, date=15): ## cron jalan di jam 12:05:00
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                if datetime.now().day == date:
                    pnr_quota_obj = self.env['tt.pnr.quota'].search([('state', '=', 'waiting'),('ho_id','=', ho_obj.id)])
                    for rec in pnr_quota_obj:
                        if rec.agent_id.is_payment_by_system:
                            rec.payment_pnr_quota_api()
                            if rec.state != 'done':
                                rec.agent_id.ban_user_api()
                                rec.state = 'failed'
                        else:
                            ## agent bill manual jika belum bayar saat cron jalan ban agent
                            if rec.state != 'done' and rec.total_amount != 0:
                                rec.agent_id.ban_user_api()
                                rec.state = 'failed'
                            elif rec.total_amount == 0: ## TOTAL BAYAR FREE
                                rec.state = 'done'

            except Exception as e:
                _logger.error(traceback.format_exc())
                self.create_cron_log_folder()
                self.write_cron_log('auto-payment quota pnr', ho_id=ho_obj.id)

    def cron_send_email_queue(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                queue_obj = self.env['tt.email.queue'].search([('ho_id','=',ho_obj.id)])
                for rec in queue_obj:
                    rec.action_send_email()
                    self.env.cr.commit()
            except:
                self.create_cron_log_folder()
                self.write_cron_log('auto-send email queue', ho_id=ho_obj.id)

    def cron_expire_unique_amount(self):
        try:
            unique_obj = self.env['unique.amount'].search([('create_date','<',datetime.now() - timedelta(days=3))])
            for rec in unique_obj:
                rec.active = False
        except:
            ## tidak tahu pakai context apa
            self.create_cron_log_folder()
            self.write_cron_log('auto-expired unique amount')

    def cron_expire_payment_acq_number(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                payment_acq = self.env['payment.acquirer.number'].search([('state', '=', 'close'), '|', ('create_date','<',datetime.now() - timedelta(hours=1)), ('time_limit','<',datetime.now()), ('ho_id','=',ho_obj.id)])
                for rec in payment_acq:
                    rec.state = 'cancel'
            except:
                self.create_cron_log_folder()
                self.write_cron_log('auto-expired payment acquirer number', ho_id=ho_obj.id)

    def cron_create_notification_agent(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                self.env['tt.agent.notification'].create_notification_record(ho_obj.id)
            except:
                self.create_cron_log_folder()
                self.write_cron_log('cron_auto_create_notification_agent', ho_id=ho_obj.id)

    def cron_inactive_dormant_users(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            self.env['res.users'].inactive_all_dormant_users(ho_obj.id, ho_obj.dormant_days_inactive)
