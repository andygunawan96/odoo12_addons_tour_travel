from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime,timedelta

_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_expired_master_event(self):
        try:
            for rec in self.sudo().env['tt.master.event'].search([('state', 'not in', ['draft', 'expired', 'postpone']), ('event_date_start', '<=', str(datetime.now()))]):
                a = False
                if rec.option_ids:
                    for opt_obj in rec.option_ids:
                        date_str = opt_obj.date_end and str(opt_obj.date_end) or opt_obj.date_start and str(opt_obj.date_start) or str(rec.event_date_start)
                        if date_str < str(datetime.now()):
                            a = True
                            break
                else:
                    if str(rec.event_date_start) < str(datetime.now()):
                        a = True
                if a:
                    rec.state = 'expired'
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto expired booking')