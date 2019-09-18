from odoo import api,models,fields
import os,traceback
from datetime import datetime

class TtCronLog(models.Model):
    _name = 'tt.cron.log'

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

    def cron_reset_payment_unique_amount(self):
        try:
            seq = self.env['ir.sequence'].search([('code','=','tt.payment.unique.amount')])
            seq.number_next_actual = 100
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-reset payment unique amount')
