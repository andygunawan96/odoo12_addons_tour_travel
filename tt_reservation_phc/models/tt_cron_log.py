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
            issued_bookings = self.env['tt.reservation.phc'].search(
                [('state','=','issued'),
                 ('state_vendor','=','confirmed_order'),
                 ('create_date','<',datetime.now())])
            for booking in issued_bookings:
                try:
                    booking.state_vendor = 'done'
                except Exception as e:
                    _logger.error(
                        '%s something failed during expired cron.\n' % (booking.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto done state vendor phc')

    def cron_auto_create_timeslot_phc(self,max_timeslot=5,adult_timeslot=420,dt_max_timeslot=1,dt_adult_timeslot=420,pcr_timeslot=150):
        try:
            #home care
            wiz_obj = self.env['create.timeslot.phc.wizard'].create({
                'end_date': datetime.today() + timedelta(days=7),
                'area_id': self.env.ref('tt_reservation_phc.tt_destination_phc_sub').id,
                'total_timeslot': max_timeslot,
                'total_adult_timeslot': adult_timeslot,
                'total_pcr_timeslot': pcr_timeslot
            })
            wiz_obj.generate_timeslot()

            #drive thru
            for idx in range(8):
                self.env['create.timeslot.phc.wizard'].generate_drivethru_timeslot((datetime.now() + timedelta(days=idx)).strftime('%Y-%m-%d'), dt_max_timeslot, dt_adult_timeslot, pcr_timeslot)
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto create timeslot phc')