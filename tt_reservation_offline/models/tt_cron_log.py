from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_update_status_booking_offline(self):
        try:
            cookie = ''
            booking_objs = self.env['tt.reservation.offline'].search([('state', 'in', ['cancel2'])])
            for rec in booking_objs:
                if rec.state == 'cancel2':
                    rec.state_offline = 'expired'
        except Exception as e:
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            self.create_cron_log_folder()
            self.write_cron_log('Update status booking Offline')
