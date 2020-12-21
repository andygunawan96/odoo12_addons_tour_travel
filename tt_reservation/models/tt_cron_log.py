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

    def cron_auto_reconcile(self,check_unreconciled_reservation=False):
        try:
            error_list = ''
            yesterday_datetime = datetime.now(pytz.timezone("Asia/Jakarta")) - timedelta(days=1)
            for provider_obj in self.env['tt.provider'].search([('is_reconcile', '=', True)]):
                wiz_obj = self.env['tt.reconcile.transaction.wizard'].create({
                    'provider_type_id': provider_obj.provider_type_id.id,
                    'provider_id': provider_obj.id,
                    'date_from': yesterday_datetime, #klo hari ini tgl 23 Jan 00:00 liat record e 22 Jan
                    'date_to': yesterday_datetime,
                })

                try:
                    recon_obj_list = wiz_obj.send_recon_request_data()
                    for recon_obj in recon_obj_list:
                        recon_obj.compare_reconcile_data()

                        # Todo: Fungsi Cek apakah masih ada data yg state issued / booked tpi blum ter reconcile
                        if check_unreconciled_reservation:
                            need_to_check_dict = recon_obj.find_unreconciled_reservation(yesterday_datetime, yesterday_datetime)
                            if need_to_check_dict:
                                try:
                                    data = {
                                        'code': 9909,
                                        'message': 'Issued in System not issued in Vendor:\n ' + recon_obj.ntc_to_str(need_to_check_dict),
                                        'provider': provider_obj.name,
                                    }
                                    self.env['tt.api.con'].send_request_to_gateway('%s/notification' % (self.env['tt.api.con'].url), data, 'notification_code')
                                except Exception as e:
                                    _logger.error('Notification Find Unreconciled Reservation.\n %s' % (traceback.format_exc()))
                            else:
                                data = {
                                    'code': 9909,
                                    'message': 'Reconcile Done, All recon. found\n ',
                                    'provider': provider_obj.name,
                                }
                                self.env['tt.api.con'].send_request_to_gateway(
                                    '%s/notification' % (self.env['tt.api.con'].url), data, 'notification_code')

                except Exception as e:
                    error_list += '%s\n%s' % (provider_obj.name,traceback.format_exc())


            if error_list:
                raise Exception("Some provider error during reconcile")
        except:
            self.create_cron_log_folder()
            self.write_cron_log('cron_auto_reconcile',error_list)