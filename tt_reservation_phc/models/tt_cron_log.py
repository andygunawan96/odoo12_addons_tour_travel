from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime,timedelta
import pytz

_logger = logging.getLogger(__name__)

class TtCronLogInhphc(models.Model):
    _inherit = 'tt.cron.log'

    def cron_reverse_issued_pending(self):
        try:
            issued_pending_bookings = self.env['tt.reservation.phc'].search(
                [('state', 'in', ['issued_pending']),
                 ('create_date','<',str(datetime.now() - timedelta(minutes=5)))])
            for booking in issued_pending_bookings:
                try:
                    if datetime.now() >= (booking.pending_date or datetime.min):
                        for provider_obj in booking.provider_ids:
                            provider_obj.action_reverse_ledger_from_button()
                            ## notif ke tele kalau ke cancel

                except Exception as e:
                    _logger.error(
                        '%s something failed during expired cron.\n' % (booking.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto expired booking')