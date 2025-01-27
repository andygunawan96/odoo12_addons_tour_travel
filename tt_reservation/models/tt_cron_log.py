from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime,timedelta
import pytz
import json
_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_expired_booking(self,auto_cancel_on_vendor=False):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                error_list = []
                for rec in variables.PROVIDER_TYPE:
                    new_bookings = self.env['tt.reservation.%s' % rec].search(
                        [('state', 'in', ['draft','booked','partial_booked', 'halt_booked']),
                         ('create_date','<',str(datetime.now() - timedelta(minutes=5))),
                         ('ho_id','=', ho_obj.id)])
                    for booking in new_bookings:
                        try:
                            if datetime.now() >= (booking.hold_date or datetime.min):
                                if rec in ['airline'] and auto_cancel_on_vendor and booking.agent_type_id.is_auto_cancel_booking:
                                    #send gateway cancel airline
                                    res = self.env['tt.%s.api.con' % rec].cancel_booking({"order_number": booking.name}, ho_id=booking.agent_id.ho_id.id)
                                    if res['error_code']:
                                        error_list.append('%s\nRESPONSE\n%s\n' % (booking.name, json.dumps(res)))
                                booking.action_expired()
                        except Exception as e:
                            _logger.error(
                                '%s something failed during expired cron.\n' % (booking.name) + traceback.format_exc())
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto expired booking', ho_id=ho_obj.id)

    def cron_sync_reservation(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                for rec in variables.PROVIDER_TYPE:
                    new_bookings = self.env['tt.reservation.%s' % rec].search(
                        [('state', 'in', ['issued']),
                         ('sync_reservation','=',False),
                         ('ho_id','=',ho_obj.id)])
                    for book_obj in new_bookings:
                        try:
                            sync = True
                            for provider in book_obj.provider_booking_ids:
                                carrier_code = []
                                if hasattr(provider, 'journey_ids'):
                                    for journey in provider.journey_ids:
                                        if hasattr(journey, 'segment_ids'):
                                            for segment in journey.segment_ids:
                                                carrier_code.append(segment.carrier_code)
                                        else:
                                            carrier_code.append(journey.carrier_code)
                                data = {
                                    'carriers': carrier_code,
                                    'pnr': book_obj.pnr,
                                    'pax': hasattr(book_obj, 'passenger_ids') and len(book_obj.passenger_ids) or 0,
                                    'provider': provider.provider_id.code,
                                    'provider_type': rec,
                                    'order_number': book_obj.name,
                                    'r_n': hasattr(book_obj, 'nights') and book_obj.nights or 0,  # room/night
                                    'ho_id': book_obj.agent_id.ho_id.id
                                }
                                # tembak gateway
                                res = self.env['tt.payment.api.con'].sync_reservation_btbo_quota_pnr(data)
                                # if res['error_code']:
                                #     sync = False
                            # if sync == True:
                            #     book_obj.sync_reservation = True
                        except Exception as e:
                            _logger.error('%s something failed during expired cron.\n' % (book_obj.name) + traceback.format_exc())
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto expired booking', ho_id=ho_obj.id)

    def cron_auto_reconcile(self,timedelta_days=1,check_unreconciled_reservation=False):
        try:
            error_list = []
            ok_provider = []
            send_notif_tele = {}
            yesterday_datetime = datetime.now(pytz.timezone("Asia/Jakarta")) - timedelta(days=timedelta_days)
            for provider_obj in self.env['tt.provider'].search([('is_reconcile', '=', True)]):
                try:
                    for provider_ho_agent_obj in self.env['tt.provider.ho.data'].search([('provider_id','=', provider_obj.id)]):
                        wiz_obj = self.env['tt.reconcile.transaction.wizard'].create({
                            'provider_type_id': provider_obj.provider_type_id.id,
                            'provider_id': provider_obj.id,
                            'date_from': yesterday_datetime,  # klo hari ini tgl 23 Jan 00:00 liat record e 22 Jan
                            'date_to': yesterday_datetime,
                            'ho_id': provider_ho_agent_obj.ho_id and provider_ho_agent_obj.ho_id.id or False
                        })
                        recon_obj_list = wiz_obj.send_recon_request_data()
                        for recon_obj in recon_obj_list:
                            recon_obj.compare_reconcile_data(notif_to_telegram=True)

                            # Todo: Fungsi Cek apakah masih ada data yg state issued / booked tpi blum ter reconcile
                            if check_unreconciled_reservation:
                                need_to_check_dict = recon_obj.find_unreconciled_reservation(yesterday_datetime, yesterday_datetime)
                                if need_to_check_dict:
                                    try:
                                        data = {
                                            'code': 9909,
                                            'message': 'Issued in System not issued in Vendor:\n' + recon_obj.ntc_to_str(need_to_check_dict),
                                            'provider': provider_obj.name,
                                        }
                                        ho_id = provider_ho_agent_obj.ho_id.id
                                        self.env['tt.api.con'].send_request_to_gateway('%s/notification' % (self.env['tt.api.con'].url), data, 'notification_code', ho_id)
                                    except Exception as e:
                                        _logger.error('Notification Find Unreconciled Reservation.\n %s' % (traceback.format_exc()))
                                else:
                                    if not send_notif_tele.get(provider_ho_agent_obj.ho_id.id):
                                        send_notif_tele[provider_ho_agent_obj.ho_id.id] = []
                                    send_notif_tele[provider_ho_agent_obj.ho_id.id].append(provider_obj.name)
                                    # ok_provider.append(provider_obj.name)


                except Exception as e:
                    error_list.append('%s\n%s\n\n' % (provider_obj.name,traceback.format_exc()))

            ## tambah context
            ## kurang test
            if send_notif_tele:
                for ho_id in send_notif_tele:
                    data = {
                        'code': 9909,
                        'message': 'Reconcile Done, Provider:\n' + '\n-'.join(send_notif_tele[ho_id]),
                        'provider': 'Cron Reconcile',
                    }
                    self.env['tt.api.con'].send_request_to_gateway('%s/notification' % (self.env['tt.api.con'].url), data, 'notification_code', ho_id=int(ho_id))

            # if ok_provider:
            #     data = {
            #         'code': 9909,
            #         'message': 'Reconcile Done, Provider:\n' + '\n-'.join(ok_provider),
            #         'provider': 'Cron Reconcile',
            #     }
            #     ## tambah context
            #     self.env['tt.api.con'].send_request_to_gateway('%s/notification' % (self.env['tt.api.con'].url), data,'notification_code')

            if error_list:
                raise Exception("Some provider error during reconcile")
        except:
            self.create_cron_log_folder()
            self.write_cron_log('cron_auto_reconcile', ''.join(error_list))

    def cron_auto_retry_issued(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                error_list = []
                for rec in variables.PROVIDER_TYPE:
                    if rec in ['airline', 'train']:
                        retry_bookings = self.env['tt.reservation.%s' % rec].search([('state', 'in', ['booked']), ('payment_method','!=', False), ('ledger_ids','!=',False), ('ho_id','=',ho_obj.id)])
                        for book_obj in retry_bookings:
                            try:
                                if book_obj.payment_date + timedelta(minutes=6) < datetime.now():
                                    seq_id = ''
                                    if book_obj.payment_acquirer_number_id:
                                        seq_id = book_obj.payment_acquirer_number_id.payment_acquirer_id.seq_id
                                    req = {
                                        'order_number': book_obj.name,
                                        'user_id': book_obj.user_id.id,
                                        'provider_type': variables.PROVIDER_TYPE_PREFIX[book_obj.name.split('.')[0]],
                                        'member': book_obj.is_member,  # kalo bayar pake BCA / MANDIRI PASTI MEMBER FALSE
                                        'acquirer_seq_id': seq_id,
                                        'force_issued': True,
                                        'ho_id': book_obj.agent_id.ho_id.id
                                    }
                                    res = self.env['tt.payment.api.con'].send_payment(req)
                                    if res['error_code'] == 0:
                                        _logger.info('##ISSUED SUCCESS##%s' % book_obj.name)
                                    else:
                                        _logger.info('##ISSUED FAIL##%s##LAST HOLDDATE: %s' % (book_obj.name, book_obj.hold_date))
                                        error_list.append('%s\nRESPONSE\n%s\n' % (book_obj.name, json.dumps(res)))
                            except Exception as e:
                                error_list.append('%s\n%s\n\n' % (book_obj.name, traceback.format_exc()))
            except:
                self.create_cron_log_folder()
                self.write_cron_log('cron_auto_retry_issued', ''.join(error_list), ho_id=ho_obj.id)