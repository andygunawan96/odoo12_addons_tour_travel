from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime,timedelta
import pytz

_logger = logging.getLogger(__name__)

class TtCronLogInhphc(models.Model):
    _inherit = 'tt.cron.log'

    def cron_auto_done_state_vendor_phc(self):
        try:
            pass
            # PHC tidak punya done, berhenti di verified
            # issued_bookings = self.env['tt.reservation.phc'].search(
            #     [('state','=','issued'),
            #      ('state_vendor','=','confirmed_order'),
            #      ('create_date','<',datetime.now())])
            # for booking in issued_bookings:
            #     try:
            #         booking.state_vendor = 'done'
            #     except Exception as e:
            #         _logger.error(
            #             '%s something failed during expired cron.\n' % (booking.name) + traceback.format_exc())
        except Exception as e:
            ## TIDAK DIPAKAI JADI TIDAK DI UPDATE
            self.create_cron_log_folder()
            self.write_cron_log('auto done state vendor phc')

    def cron_auto_create_timeslot_phc(self,days_range=1,max_timeslot=3,adult_timeslot=425,dt_max_timeslot=1,dt_days_range=8,dt_adult_timeslot=425,pcr_timeslot=200):
        try:
            #home care
            wiz_obj = self.env['create.timeslot.phc.wizard'].create({
                'end_date': datetime.today() + timedelta(days=days_range),
                'area_id': self.env.ref('tt_reservation_phc.tt_destination_phc_sub').id,
                'default_data_id': self.env['tt.timeslot.phc.default'].search([],limit=1).id,
                'total_timeslot': max_timeslot,
                'total_adult_timeslot': adult_timeslot,
                'total_pcr_timeslot': pcr_timeslot
            })
            wiz_obj.generate_timeslot()
            public_holiday_res = self.env['tt.public.holiday'].get_public_holiday_api({
                'start_date': datetime.now(),
                'end_date': datetime.now() + timedelta(days=8)
            }, False)
            public_holiday_list = [str(rec['date']) for rec in public_holiday_res['response']]
            #drive thru
            for idx in range(dt_days_range):
                this_date = datetime.now() + timedelta(days=idx)
                if str(this_date.date()) in public_holiday_list or this_date.weekday() == 6:
                    continue
                self.env['create.timeslot.phc.wizard'].generate_drivethru_timeslot(this_date.strftime('%Y-%m-%d'), dt_max_timeslot, dt_adult_timeslot, pcr_timeslot)
        except Exception as e:
            ## TIDAK DIPAKAI JADI TIDAK DI UPDATE
            self.create_cron_log_folder()
            self.write_cron_log('auto create timeslot phc')

    def cron_auto_notification_timeslot_quota_data_phc(self):
        try:
            data = {
                'code': 9909,
                'message': "Daily Summary\n\n %s" % (self.env['tt.reservation.phc'].get_verified_summary())
            }
            ## tambah context
            ## TIDAK DIPAKAI JADI TIDAK DI UPDATE
            self.env['tt.api.con'].send_request_to_gateway('%s/notification' % (self.env['tt.api.con'].url), data,
                                                           'notification_code')
        except Exception as e:
            ## TIDAK DIPAKAI JADI TIDAK DI UPDATE
            self.create_cron_log_folder()
            self.write_cron_log('auto notification timeslot quota data phc')

    def cron_auto_sync_verification_data_phc(self):
        try:
            book_objs = self.env['tt.reservation.phc'].search([('state_vendor', '=', 'new_order'),('state','=','issued')])
            for book_obj in book_objs:
                book_obj.sync_verified_with_phc()
        except Exception as e:
            ## TIDAK DIPAKAI JADI TIDAK DI UPDATE
            self.create_cron_log_folder()
            self.write_cron_log('auto sync verification data phc')