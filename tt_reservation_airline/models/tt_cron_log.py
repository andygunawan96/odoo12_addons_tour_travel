from odoo import api,models,fields
from ...tools import variables
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
        try:
            # Notification Dupe Booking GDS & NDC
            # - Pax sama ( Name & Birth date or passport )
            # - Pernah berangkat OW & Booking lagi di tanggal OW
            # - Pernah berangkat RT/MC & Booking lagi waktu belum pulang

            # Notification Dupe Lion:
            # - Segment sama dalam kondisi Book 9 atau lebih pax

            #### LION 1 SEGMENT TOO MANY PAX ###
            LION_PAX_RULES = 9
            lion_segment_objs = self.env['tt.segment.airline'].search([('booking_id.state','=','booked'),
                                                                       ('provider_id','in',
                                                                        [self.env.ref('tt_reservation_airline.tt_provider_airline_lionair').id,
                                                                        self.env.ref('tt_reservation_airline.tt_provider_airline_lionairapi').id])])
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
                                                                         self.env.ref('tt_reservation_airline.tt_provider_airline_singaporeairlines').id])])

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
            ctr = 0
            for values in segment_dict.values():
                if values['illegal']:
                    ctr += 1
                    temp_lion_msg = '%s. %s PAX\n%s\n' % (ctr,values['pax'], '\n'.join(values['pax_code_list']))#ctr, pax count, pnr code list
                    self.manage_msg_length(messages_lion_dict,temp_lion_msg,"LION\n")

            messages_gds_dict = {
                "ctr": 0
            }
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
                    ctr += 1
                    temp_gds_msg = '%s. %s%s\n\n' % (ctr, pax_code, dupes_msg)#counter, pax name, pnr code list
                    self.manage_msg_length(messages_gds_dict, temp_gds_msg,"GDS\n")

            if messages_lion_dict:
                self.env['tt.airline.api.con'].send_duplicate_segment_notification(messages_lion_dict)
            if messages_gds_dict:
                self.env['tt.airline.api.con'].send_duplicate_segment_notification(messages_gds_dict)
            # send_duplicate_segment_notification
        except Exception as e:
            raise(e)

    def manage_msg_length(self,msg_dict,param_msg,add_msg):
        TELEGRAM_MSG_LIMIT = 3800
        if msg_dict['ctr'] not in msg_dict:
            msg_dict[msg_dict['ctr']] = add_msg
        len_msg = len(param_msg)
        len_d_msg = len(msg_dict[msg_dict['ctr']])
        if len_msg + len_d_msg > TELEGRAM_MSG_LIMIT: ## OUT OF BOUND
            ## SPLIT MSG INTO 2, still within limit and leftover passed into recursive
            n_index = param_msg[:TELEGRAM_MSG_LIMIT-len_d_msg].rfind('\n')
            kept_msg = param_msg[:n_index]
            leftover_msg = param_msg[n_index:]
            ##

            msg_dict[msg_dict['ctr']] += kept_msg
            msg_dict['ctr'] += 1
            self.manage_msg_length(msg_dict,leftover_msg,add_msg)##send leftover msg to recrursive
        else:
            msg_dict[msg_dict['ctr']] += param_msg
