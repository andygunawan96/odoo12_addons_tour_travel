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

    def cron_auto_create_timeslot_phc(self):
        try:
            #home care
            wiz_obj = self.env['create.timeslot.phc.wizard'].create({
                'end_date': datetime.today() + timedelta(days=7),
                'area_id': self.env.ref('tt_reservation_phc.tt_destination_phc_sub').id
            })
            wiz_obj.generate_timeslot()

            #drive thru
            wiz_obj = self.env['create.timeslot.phc.wizard'].create({
                'end_date': datetime.today() + timedelta(days=2),
                'area_id': self.env.ref('tt_reservation_phc.tt_destination_phc_sub').id,
                'timeslot_type': 'drive_thru'
            })
            wiz_obj.generate_timeslot()
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto create timeslot phc')