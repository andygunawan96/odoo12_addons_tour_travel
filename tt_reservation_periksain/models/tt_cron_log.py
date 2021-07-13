from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime,timedelta
import pytz
import json

_logger = logging.getLogger(__name__)

class TtCronLogInhPeriksain(models.Model):
    _inherit = 'tt.cron.log'

    # def cron_reverse_issued_pending(self):
    #     try:
    #         issued_pending_bookings = self.env['tt.reservation.periksain'].search(
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

    def cron_auto_done_state_vendor_periksain(self):
        try:
            issued_bookings = self.env['tt.reservation.periksain'].search(
                [('state','=','issued'),
                 ('state_vendor','=','confirmed_order'),
                 ('create_date','<',datetime.now()-timedelta(days=1))])
            for booking in issued_bookings:
                try:
                    booking.state_vendor = 'done'
                except Exception as e:
                    _logger.error(
                        '%s something failed during expired cron.\n' % (booking.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto done state vendor periksain')

    def cron_auto_create_timeslot_periksain(self):
        try:
            res = self.env['tt.timeslot.periksain'].get_config_cron()
            kota_list = []
            jenis_tindakan = {}
            time_string = ''
            id_time_string = ''
            for rec in res['response']['kota']:
                kota_list.append(rec['kabupaten']['nama'])
            for idx, rec in enumerate(res['response']['time']):
                if idx != 0:
                    time_string += ','
                    id_time_string += ','
                time_string += rec['jam_awal']
                id_time_string += str(rec['id'])

            for rec in res['response']['tindakan_pemeriksaan']:
                jenis_tindakan[rec['id']] = {
                    "name": rec['tindakan']['nama'],
                    "code": rec['tindakan']['kode']
                }

            print(res)
            for rec in self.env['tt.destinations'].search(
                    [('provider_type_id','=',self.env.ref('tt_reservation_periksain.tt_provider_type_periksain').id)]):
                for kota in res['response']['kota']:
                    if rec.name in kota['kabupaten']['nama']:
                        # CREATE
                        wiz_obj = self.env['create.timeslot.periksain.wizard'].create({
                            'end_date': datetime.today() + timedelta(days=7),
                            'area_id': rec.id,
                            'time_string': time_string,
                            'id_kota_vendor': kota['id'],
                            'id_time_vendor': id_time_string,
                            'id_jenis_tindakan_vendor': json.dumps(jenis_tindakan)
                        })
                        wiz_obj.generate_timeslot()
                        break
            # time_string
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto create timeslot periksain')