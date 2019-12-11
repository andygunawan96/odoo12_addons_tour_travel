from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_expired_booking(self):
        try:
            for rec in variables.PROVIDER_TYPE:
                new_bookings = self.env['tt.reservation.%s' % rec].search(
                    [('state', '=', 'booked')])
                for booking in new_bookings:
                    try:
                        if datetime.now() >= (booking.hold_date or datetime.min):
                            booking.action_expired()
                    except Exception as e:
                        _logger.error(
                            '%s something failed during expired cron.\n' % (booking.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-reset payment unique amount')