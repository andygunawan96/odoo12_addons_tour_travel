from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime,timedelta
import pytz

_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_expired_booking(self):
        try:
            for rec in variables.PROVIDER_TYPE:
                new_bookings = self.env['tt.reservation.%s' % rec].search(
                    [('state', 'in', ['draft','booked','partial_booked']),
                     ('create_date','<',str(datetime.now() - timedelta(minutes=5)))])
                for booking in new_bookings:
                    try:
                        if datetime.now() >= (booking.hold_date or datetime.min):
                            booking.action_expired()
                    except Exception as e:
                        _logger.error(
                            '%s something failed during expired cron.\n' % (booking.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto expired booking')

    def cron_auto_reconcile(self):
        try:
            for provider_obj in self.env['tt.provider'].search([('is_reconcile', '=', True)]):
                wiz_obj = self.env['tt.reconcile.transaction.wizard'].create({
                    'provider_type_id': provider_obj.provider_type_id.id,
                    'provider_id': provider_obj.id,
                    'date_from': datetime.now(pytz.timezone("Asia/Jakarta")) - timedelta(days=1), #klo hari ini tgl 23 Jan 00:00 liat record e 22 Jan
                    'date_to': datetime.now(pytz.timezone("Asia/Jakarta")) - timedelta(days=1),
                })
                recon_obj = wiz_obj.send_recon_request_data()
                recon_obj.compare_reconcile_data()
        except:
            self.create_cron_log_folder()
            self.write_cron_log('cron_auto_reconcile')
