from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_expire_top_up(self):
        try:
            new_top_up = self.env['tt.top.up'].search([('state', '=', 'request')])
            for top_up in new_top_up:
                try:
                    if datetime.now() >= (top_up.due_date or datetime.min):
                        top_up.action_expired_top_up()
                except Exception as e:
                    _logger.error('%s something failed during expired cron.\n' % (top_up.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-reset payment unique amount')