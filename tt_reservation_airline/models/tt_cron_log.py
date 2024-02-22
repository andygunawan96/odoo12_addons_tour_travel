from odoo import api,models,fields
from ...tools import variables, util
import logging,traceback
from datetime import datetime,timedelta
import pytz

_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_sync_booking(self):
        book_objs = self.env['tt.reservation.airline'].search([('is_hold_date_sync', '=', False),
                                                               ('state','in',['partial_booked','partial_issued','booked']),
                                                               ('create_date','>=',(datetime.now() - timedelta(1)))])
        _logger.info("### CRON SYNC ###")
        _logger.info(book_objs.ids)
        for rec in book_objs:
            req = {
                'order_number': rec.name,
                'user_id': rec.booked_uid.id
            }
            self.env['tt.airline.api.con'].send_get_booking_for_sync(req)

    def cron_notify_duplicate_booking(self):
        _logger.info("CRON NOTIFY DUPLICATE BOOKING - START")
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                # Notification Dupe Booking GDS & NDC
                # - Pax sama ( Name & Birth date or passport )
                # - Pernah berangkat OW & Booking lagi di tanggal OW
                # - Pernah berangkat RT/MC & Booking lagi waktu belum pulang

                # Notification Dupe Hidden Group Booking:
                # - Segment sama dalam kondisi Book 9 atau lebih pax

                #### Hidden Group Booking 1 SEGMENT TOO MANY PAX ###
                LION_PAX_RULES = 11
                lion_segment_objs = self.env['tt.segment.airline'].search([('booking_id.state','=','booked'),
                                                                           ('provider_id','in',
                                                                            [self.env.ref('tt_reservation_airline.tt_provider_airline_lionair').id,
                                                                             self.env.ref('tt_reservation_airline.tt_provider_airline_lionairapi').id,
                                                                             self.env.ref('tt_reservation_airline.tt_provider_airline_amadeus').id,
                                                                             self.env.ref('tt_reservation_airline.tt_provider_airline_singaporeairlines').id]),
                                                                           ('booking_id.ho_id','=',ho_obj.id)])
                segment_dict = {}
                for segment_obj in lion_segment_objs:
                    segment_code = segment_obj.segment_code
                    segment_pnr_code = '%s %s %s' % (segment_obj.pnr and segment_obj.pnr or '#NOPNR',segment_obj.booking_id.name,segment_obj.name)
                    segment_pax_count = segment_obj.booking_id.adult + segment_obj.booking_id.child # assume infant wont count
                    if segment_code not in segment_dict:
                        segment_dict[segment_code] = {
                            'pax': 0,
                            'pax_code_list': [],
                            'illegal': False
                        }
                    segment_dict[segment_code]['pax'] += segment_pax_count
                    segment_dict[segment_code]['pax_code_list'].append(segment_pnr_code)
                    if segment_dict[segment_code]['pax'] >= LION_PAX_RULES and not segment_dict[segment_code]['illegal']:
                        segment_dict[segment_code]['illegal'] = True

                ###########################################################################################

                ## GDS & NDC DUPE PAX

                gds_segment_objs = self.env['tt.segment.airline'].search([('booking_id.state', '=', 'booked'),
                                                                          ('provider_id', 'in',
                                                                            [self.env.ref('tt_reservation_airline.tt_provider_airline_amadeus').id,
                                                                             self.env.ref('tt_reservation_airline.tt_provider_airline_singaporeairlines').id]),
                                                                          ('booking_id.ho_id', '=', ho_obj.id)])

                pax_dict = {}
                pnr_departure_count_dict = {}
                for segment_obj in gds_segment_objs:
                    departure_date = segment_obj.departure_date[:10]
                    segment_pnr_code = '%s %s' % (segment_obj.pnr and segment_obj.pnr or '#NOPNR',segment_obj.booking_id.name)
                    for pax_obj in segment_obj.booking_id.passenger_ids:
                        pax_code = pax_obj.identity_number and '%s | %s' % (pax_obj.name,pax_obj.identity_number) or '%s | %s' % (pax_obj.name,pax_obj.birth_date)
                        if pax_code not in pax_dict:
                            pax_dict[pax_code] = {}
                        if segment_pnr_code not in pax_dict[pax_code]:
                            pax_dict[pax_code][segment_pnr_code] = {}
                        if departure_date not in pax_dict[pax_code][segment_pnr_code]:
                            pax_dict[pax_code][segment_pnr_code][departure_date] = 0
                        pax_dict[pax_code][segment_pnr_code][departure_date] += 1

                        if pax_code not in pnr_departure_count_dict:
                            pnr_departure_count_dict[pax_code] = {}
                        if departure_date not in pnr_departure_count_dict[pax_code]:
                            pnr_departure_count_dict[pax_code][departure_date] = 0
                        pnr_departure_count_dict[pax_code][departure_date] += 1

                messages_lion_dict = {
                    "ctr": 0
                }## to separate long messages
                ## Make the messages
                qty_ctr = 0
                for values in segment_dict.values():
                    if values['illegal']:
                        qty_ctr += 1
                        temp_lion_msg = '%s. %s PAX\n%s\n' % (qty_ctr,values['pax'], '\n'.join(values['pax_code_list']))#ctr, pax count, pnr code list
                        util.manage_msg_length(messages_lion_dict,temp_lion_msg,"Hidden Group\n")

                messages_gds_dict = {
                    "ctr": 0
                }
                qty_ctr = 0
                for pax_code,segment_pnr_code_dict in pax_dict.items():
                    # only 1 segment no need to check
                    if len(segment_pnr_code_dict) <= 1:
                        continue

                    dupes_msg = ''
                    for segment_pnr_code,dep_date_dict in segment_pnr_code_dict.items():
                        for departure_date, dep_count in dep_date_dict.items():
                            if pnr_departure_count_dict[pax_code][departure_date] > dep_count:
                                dupes_msg += '\n%s | %s' % (segment_pnr_code, departure_date)#pax name, pnr code list

                    if dupes_msg:
                        qty_ctr += 1
                        temp_gds_msg = '%s. %s%s\n\n' % (qty_ctr, pax_code, dupes_msg)#counter, pax name, pnr code list
                        util.manage_msg_length(messages_gds_dict, temp_gds_msg,"GDS\n")
                ## tambah context
                ## kurang test
                if messages_lion_dict:
                    self.env['tt.airline.api.con'].send_duplicate_segment_notification(messages_lion_dict, ho_obj.id)
                if messages_gds_dict:
                    self.env['tt.airline.api.con'].send_duplicate_segment_notification(messages_gds_dict, ho_obj.id)
                # send_duplicate_segment_notification

            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('cron notify duplicate booking', ho_id=ho_obj.id)

        _logger.info("CRON NOTIFY DUPLICATE BOOKING - END")

    def cron_check_segment_booking_amadeus(self):
        _logger.info('Cron Check Segment Booking Amadeus : START')
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                state_list = ['issued', 'cancel', 'cancel2']
                provider_list = ['amadeus']
                now_obj = datetime.now()
                start_obj = now_obj - timedelta(days=1)
                start_obj = start_obj.replace(hour=0, minute=0, second=0)
                end_obj = now_obj + timedelta(days=1)
                end_obj = end_obj.replace(hour=23, minute=59, second=59)

                params = [
                    ('departure_date', '>=', start_obj),
                    ('departure_date', '<=', end_obj),
                    ('booking_id.ho_id','=', ho_obj.id)
                ]

                pnr_list = []
                provider_id_list = []
                provider_obj_list = []
                objs = self.env['tt.segment.airline'].search(params)
                for obj in objs:
                    try:
                        if not obj.journey_id:
                            continue

                        journey_obj = obj.journey_id
                        if not journey_obj.provider_booking_id:
                            continue

                        provider_obj = journey_obj.provider_booking_id
                        if provider_obj.state not in state_list:
                            continue
                        pnr = provider_obj.pnr
                        pnr2 = provider_obj.pnr2
                        reference = provider_obj.reference
                        if not pnr:
                            continue
                        if pnr in pnr_list:
                            continue
                        pnr_list.append(pnr)
                        provider = provider_obj.provider_id.code if provider_obj.provider_id else ''
                        if not provider:
                            continue
                        if provider != 'amadeus':
                            continue

                        if not pnr2:
                            pnr2 = pnr
                        if not reference:
                            reference = pnr

                        provider_id = provider_obj.id
                        if provider_id in provider_id_list:
                            continue
                        provider_id_list.append(provider_id)
                        provider_obj_list.append(provider_obj)
                    except:
                        _logger.error('Cron Check Segment Booking Amadeus, Error Extract Data, %s' % traceback.format_exc())

                _logger.info('Check Segment Booking Amadeus, %s record(s) found' % len(provider_obj_list))
                for prov_obj in provider_obj_list:
                    try:
                        _logger.info('Cron Check Segment Booking Amadeus, Action Check PNR %s' % prov_obj.pnr)
                        prov_obj.action_check_segment_provider()
                    except:
                        _logger.error('Cron Check Segment Booking Amadeus, Action Check PNR %s, %s' % (prov_obj.pnr, traceback.format_exc()))
            except:
                _logger.error('Error Cron Check Segment Booking Amadeus, %s' % traceback.format_exc())
                self.create_cron_log_folder()
                self.write_cron_log('cron auto check segment booking amadeus', ho_id=ho_obj.id)
        _logger.info('Cron Check Segment Booking Amadeus : END')
