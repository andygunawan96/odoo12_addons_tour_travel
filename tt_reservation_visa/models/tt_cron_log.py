from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_update_status_booking_visa(self):
        try:
            cookie = ''
            booking_objs = self.env['tt.reservation.visa'].search([('state_visa', 'in', ['delivered'])])
            for rec in booking_objs:
                if rec.state_visa == 'delivered':
                    if rec.delivered_date:
                        delivered_date = rec.delivered_date
                        if delivered_date < datetime.now() + timedelta(days=1):
                            rec.action_done_visa()
                    else:
                        rec.delivered_date = datetime.now()
        except Exception as e:
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            self.create_cron_log_folder()
            self.write_cron_log('Update status booking Visa')