from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime,timedelta
import pytz
import json

_logger = logging.getLogger(__name__)

class TtCronLogInhLabPintar(models.Model):
    _inherit = 'tt.cron.log'

    # def cron_reverse_issued_pending(self):
    #     try:
    #         issued_pending_bookings = self.env['tt.reservation.labpintar'].search(
    #             [('state', 'in', ['issued_pending']),
    #              ('create_date','<',str(datetime.now() - timedelta(minutes=5)))])
    #         for booking in issued_pending_bookings:
    #             try:
    #                 if datetime.now() >= (booking.pending_date or datetime.min):
    #                     for provider_obj in booking.provider_ids:
    #                         provider_obj.action_reverse_ledger_from_button()
    #                         ## notif ke tele kalau ke cancel
    #
    #             except Exception as e:
    #                 _logger.error(
    #                     '%s something failed during expired cron.\n' % (booking.name) + traceback.format_exc())
    #     except Exception as e:
    #         self.create_cron_log_folder()
    #         self.write_cron_log('auto expired booking')

    def cron_auto_done_state_vendor_labpintar(self):
        try:
            issued_bookings = self.env['tt.reservation.labpintar'].search(
                [('state','=','issued'),
                 ('state_vendor','in',['confirmed_order', 'test_completed']),
                 ('create_date','<',datetime.now()-timedelta(days=1))])
            for booking in issued_bookings:
                try:
                    booking.state_vendor = 'done'
                except Exception as e:
                    _logger.error(
                        '%s something failed during expired cron.\n' % (booking.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto done state vendor lab pintar')

    def cron_auto_create_timeslot_labpintar(self):
        try:
            time_string = ''
            list_jam_default = "08:00,09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,18:00" ## DEFAULT JAM
            time_string_list = []
            for rec_default_time in list_jam_default.split(','):
                if not any(rec_data['time'] == rec_default_time for rec_data in time_string_list):
                    time_string_list.append({
                        "time": rec_default_time
                    })
            time_string_list = sorted(time_string_list, key=lambda k: k['time'])
            for idx, rec in enumerate(time_string_list):
                if idx != 0:
                    time_string += ','
                time_string += rec['time']
            for rec in self.env['tt.destinations'].search(
                    [('provider_type_id','=',self.env.ref('tt_reservation_labpintar.tt_provider_type_labpintar').id)]):
                # CREATE
                wiz_obj = self.env['create.timeslot.labpintar.wizard'].create({
                    'end_date': datetime.today() + timedelta(days=3),
                    'area_id': rec.id,
                    'time_string': time_string,
                })
                wiz_obj.generate_timeslot(True)
            # time_string
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto create timeslot labpintar')