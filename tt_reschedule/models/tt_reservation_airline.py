from odoo import api,models,fields, _
from ...tools.ERR import RequestException
from ...tools import util,variables,ERR
import logging,traceback
import json

_logger = logging.getLogger(__name__)


class ReservationAirline(models.Model):

    _inherit = "tt.reservation.airline"

    reschedule_ids = fields.One2many('tt.reschedule', 'res_id', 'After Sales', readonly=True)

    def create_reschedule_airline_api(self, vals, context):
        try:
            # print('Create Reschedule Request, %s' % json.dumps(vals))
            airline_obj = self.env['tt.reservation.airline'].search([('name', '=', vals['order_number'])], limit=1)
            if airline_obj:
                airline_obj = airline_obj[0]
                passenger_list = []
                for rec in airline_obj.passenger_ids:
                    passenger_list.append(rec.id)
                old_segment_list = []
                new_segment_list = []
                for rec in airline_obj.segment_ids:
                    old_segment_list.append(rec.id)

                # July 9, 2020 - SAM
                # Mengambil data dari gateway
                # admin_fee_obj = None
                # July 13, 2020 - SAM
                # Sementara untuk payment acquirer id diambil dari default agent id
                # payment_acquirer_obj = None
                payment_acquirer_obj = airline_obj.agent_id.default_acquirer_id
                # END

                if vals.get('seq_id'):
                    payment_acquirer_obj = self.env['payment.acquirer'].search([('seq_id', '=', vals['seq_id'])], limit=1)
                if not payment_acquirer_obj:
                    return ERR.get_error(1017)

                total_amount = 0.0
                # reschedule_type = ''
                if vals.get('sell_reschedule_provider'):
                    # reschedule_type = 'reschedule'
                    # admin_fee_obj = self.env.ref('tt_accounting.admin_fee_reschedule')
                    for prov in vals['sell_reschedule_provider']:
                        for journey in prov['journeys']:
                            for seg in journey['segments']:
                                carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', seg['carrier_code'])], limit=1)
                                provider_obj = self.env['tt.provider'].sudo().search([('code', '=', seg['provider'])], limit=1)
                                origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['origin'])], limit=1)
                                destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['destination'])], limit=1)
                                n_seg_values = {
                                    'segment_code': seg['segment_code'],
                                    'pnr': prov['pnr'],
                                    'fare_code': '',
                                    'carrier_code': seg['carrier_code'],
                                    'carrier_number': seg['carrier_number'],
                                    'origin_terminal': seg['origin_terminal'],
                                    'destination_terminal': seg['destination_terminal'],
                                    'departure_date': seg['departure_date'],
                                    'arrival_date': seg['arrival_date'],
                                    'class_of_service': seg.get('class_of_service') or '', #di connector uda kasih di webservice hilang
                                    'cabin_class': '',
                                    'sequence': seg.get('sequence', 0),
                                }
                                if carrier_obj:
                                    n_seg_values['carrier_id'] = carrier_obj.id
                                if provider_obj:
                                    n_seg_values['provider_id'] = provider_obj.id
                                if origin_obj:
                                    n_seg_values['origin_id'] = origin_obj.id
                                if destination_obj:
                                    n_seg_values['destination_id'] = destination_obj.id

                                for fare in seg['fares']:
                                    n_seg_values.update({
                                        'fare_code': fare['fare_code'],
                                        'class_of_service': fare['class_of_service'],
                                        'cabin_class': fare['cabin_class'],
                                    })
                                    for sc in fare['service_charge_summary']:
                                        total_amount += sc['total_price']

                                n_seg_obj = self.env['tt.segment.reschedule'].sudo().create(n_seg_values)
                                new_segment_list.append(n_seg_obj.id)

                                # October 20, 2020 - SAM
                                # FIXME sementara di comment dan diambil dari segment, karena butuh cepat untuk video
                                # FIXME tunggu update dari gateway
                                leg_values = {
                                    'segment_id': n_seg_obj.id,
                                    'origin_terminal': n_seg_values['origin_terminal'],
                                    'destination_terminal': n_seg_values['destination_terminal'],
                                    'departure_date': n_seg_values['departure_date'],
                                    'arrival_date': n_seg_values['arrival_date'],
                                }
                                if n_seg_values.get('carrier_id'):
                                    leg_values.update({
                                        'carrier_id': n_seg_values['carrier_id']
                                    })

                                if n_seg_values.get('provider_id'):
                                    leg_values.update({
                                        'provider_id': n_seg_values['provider_id']
                                    })

                                if n_seg_values.get('origin_id'):
                                    leg_values.update({
                                        'origin_id': n_seg_values['origin_id']
                                    })

                                if n_seg_values.get('destination_id'):
                                    leg_values.update({
                                        'destination_id': n_seg_values['destination_id']
                                    })
                                self.env['tt.leg.reschedule'].sudo().create(leg_values)
                                # for leg in seg['legs']:
                                #     leg_carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', leg['carrier_code'])], limit=1)
                                #     leg_provider_obj = self.env['tt.provider'].sudo().search([('code', '=', leg['provider'])], limit=1)
                                #     leg_origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', leg['origin'])], limit=1)
                                #     leg_destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', leg['destination'])], limit=1)
                                #
                                #     leg_values = {
                                #         'segment_id': n_seg_obj.id,
                                #         'origin_terminal': leg['origin_terminal'],
                                #         'destination_terminal': leg['destination_terminal'],
                                #         'departure_date': leg['departure_date'],
                                #         'arrival_date': leg['arrival_date'],
                                #     }
                                #     if leg_carrier_obj:
                                #         leg_values.update({
                                #             'carrier_id': leg_carrier_obj.id
                                #         })
                                #
                                #     if leg_provider_obj:
                                #         leg_values.update({
                                #             'provider_id': leg_provider_obj.id
                                #         })
                                #
                                #     if leg_origin_obj:
                                #         leg_values.update({
                                #             'origin_id': leg_origin_obj.id
                                #         })
                                #
                                #     if leg_destination_obj:
                                #         leg_values.update({
                                #             'destination_id': leg_destination_obj.id
                                #         })
                                #     self.env['tt.leg.reschedule'].sudo().create(leg_values)

                else:
                    for seg in airline_obj.segment_ids:
                        n_seg_values = {
                            'segment_code': seg.segment_code,
                            'pnr': seg.pnr,
                            'fare_code': seg.fare_code,
                            'carrier_code': seg.carrier_code,
                            'carrier_number': seg.carrier_number,
                            'origin_terminal': seg.origin_terminal,
                            'destination_terminal': seg.destination_terminal,
                            'departure_date': seg.departure_date,
                            'arrival_date': seg.arrival_date,
                            'class_of_service': seg.class_of_service,
                            'cabin_class': seg.cabin_class,
                            'sequence': seg.sequence,
                        }
                        if seg.carrier_id:
                            n_seg_values['carrier_id'] = seg.carrier_id.id
                        if seg.provider_id:
                            n_seg_values['provider_id'] = seg.provider_id.id
                        if seg.origin_id:
                            n_seg_values['origin_id'] = seg.origin_id.id
                        if seg.destination_id:
                            n_seg_values['destination_id'] = seg.destination_id.id

                        n_seg_obj = self.env['tt.segment.reschedule'].sudo().create(n_seg_values)
                        new_segment_list.append(n_seg_obj.id)

                        for leg in seg.leg_ids:
                            leg_values = {
                                'segment_id': n_seg_obj.id,
                                'leg_code': leg.leg_code,
                                'origin_id': leg.origin_id.id,
                                'destination_id': leg.destination_id.id,
                                'origin_terminal': leg.origin_terminal,
                                'destination_terminal': leg.destination_terminal,
                                'departure_date': leg.departure_date,
                                'arrival_date': leg.arrival_date,
                            }
                            self.env['tt.leg.reschedule'].sudo().create(leg_values)
                # END

                # for rec in vals['segments']:
                #     temp_carrier_id = rec.get('carrier_code') and self.env['tt.transport.carrier'].sudo().search([('code', '=', rec['carrier_code'])], limit=1) or []
                #     if temp_carrier_id:
                #         temp_carrier_id = temp_carrier_id[0]
                #     temp_provider_id = rec.get('provider_code') and self.env['tt.provider'].sudo().search([('code', '=', rec['provider_code'])], limit=1) or []
                #     if temp_provider_id:
                #         temp_provider_id = temp_provider_id[0]
                #     temp_origin_id = rec.get('origin') and self.env['tt.destinations'].sudo().search([('code', '=', rec['origin'])], limit=1) or []
                #     if temp_origin_id:
                #         temp_origin_id = temp_origin_id[0]
                #     temp_destination_id = rec.get('destination') and self.env['tt.destinations'].sudo().search([('code', '=', rec['destination'])], limit=1) or []
                #     if temp_destination_id:
                #         temp_destination_id = temp_destination_id[0]
                #     new_seg_obj = self.env['tt.segment.reschedule'].sudo().create({
                #         'segment_code': rec.get('segment_code', ''),
                #         'pnr': rec.get('pnr', ''),
                #         'fare_code': rec.get('fare_code', ''),
                #         'carrier_id': temp_carrier_id.id,
                #         'carrier_code': rec.get('carrier_code', ''),
                #         'carrier_number': rec.get('carrier_number', ''),
                #         'provider_id': temp_provider_id.id,
                #         'origin_id': temp_origin_id.id,
                #         'destination_id': temp_destination_id.id,
                #         'origin_terminal': rec.get('origin_terminal', ''),
                #         'destination_terminal': rec.get('destination_terminal', ''),
                #         'departure_date': rec.get('departure_date', ''),
                #         'arrival_date': rec.get('arrival_date', ''),
                #         'class_of_service': rec.get('class_of_service', ''),
                #         'cabin_class': rec.get('cabin_class', ''),
                #         'sequence': rec.get('sequence', 0),
                #     })
                #     new_segment_list.append(new_seg_obj.id)

                # if not admin_fee_obj or not reschedule_type or not payment_acquirer_obj:
                if not payment_acquirer_obj:
                    raise Exception('Empty required field, Payment Acquirer Obj : %s' % (1 if payment_acquirer_obj else 0))

                # July 9, 2020 - SAM
                # Menambahkan untuk field harga
                # rsch_line_values = {
                #     'reschedule_type': reschedule_type,
                #     'reschedule_amount': total_amount,
                #     'reschedule_amount_ho': total_amount,
                #     'real_reschedule_amount': total_amount,
                #     'admin_fee_id': admin_fee_obj.id,
                #     'admin_fee': admin_fee_obj.amount,
                # }
                # rsch_line_obj = self.env['tt.reschedule.line'].sudo().create(rsch_line_values)
                # reschedule_line_list = [rsch_line_obj.id]
                # END

                res_vals = {
                    'agent_id': airline_obj.agent_id.id,
                    'customer_parent_id': airline_obj.customer_parent_id.id,
                    'booker_id': airline_obj.booker_id.id,
                    'currency_id': airline_obj.currency_id.id,
                    'service_type': airline_obj.provider_type_id.id,
                    'referenced_pnr': airline_obj.pnr,
                    'old_segment_ids': [(6, 0, old_segment_list)],
                    'new_segment_ids': [(6, 0, new_segment_list)],
                    # 'reschedule_line_ids': [(6, 0, reschedule_line_list)],
                    'passenger_ids': [(6, 0, passenger_list)],
                    'res_model': airline_obj._name,
                    'res_id': airline_obj.id,
                    'notes': vals.get('notes') and vals['notes'] or '',
                    'payment_acquirer_id': payment_acquirer_obj.id,
                    'created_by_api': True,
                }
                res_obj = self.env['tt.reschedule'].create(res_vals)
                # res_obj.confirm_reschedule_from_button()
                # res_obj.send_reschedule_from_button()
                # res_obj.validate_reschedule_from_button()
                # res_obj.finalize_reschedule_from_button()
                # res_obj.action_done()
                final_res = {
                    'reschedule_number': res_obj.name,
                    'reschedule_id': res_obj.id,
                }
                return ERR.get_no_error(final_res)
            else:
                raise RequestException(1001, additional_message="Airline reservation %s is not found in our system." % (vals['order_number']))
        except RequestException as e:
            _logger.error('Error Create Reschedule Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Create Reschedule Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1030)

    def update_reschedule_airline_api(self, vals, context):
        try:
            if vals.get('reschedule_id'):
                reschedule_obj = self.env['tt.reschedule'].browse(vals['reschedule_id'])
            elif vals.get('reschedule_number'):
                reschedule_obj = self.env['tt.reschedule'].search([('name', '=', vals['reschedule_number'])])
            else:
                raise Exception('Reschedule Object not found')

            total_amount = 0.0
            reschedule_type = ''
            note_list = []
            admin_fee_obj = None
            reschedule_line_list = []
            for rec in vals['update_booking_provider']:
                total_amount = 0.0
                if rec.get('status', 'FAILED') == 'FAILED':
                    continue

                admin_fee_obj = self.env.ref('tt_accounting.admin_fee_reschedule')
                for journey in rec['journeys']:
                    reschedule_type = 'reschedule'
                    for seg in journey['segments']:
                        for fare in seg['fares']:
                            for sc_sum in fare['service_charge_summary']:
                                total_amount += sc_sum['total_price']

                for psg in rec['passengers']:
                    if not psg.get('fees'):
                        continue

                    note_list.append('Name : %s' % (psg['first_name']))
                    for fee in psg['fees']:
                        reschedule_type = 'addons'
                        total_amount += fee['base_price']
                        text = '%s (%s, %s) : %s' % (fee['fee_name'], fee['fee_type'], fee['fee_code'], fee['base_price'])
                        note_list.append(text)
                    note_list.append('')

                if not reschedule_type or not admin_fee_obj:
                    raise Exception('Required Field is not set, Reschedule Type : %s, Admin Fee Obj : %s' % (reschedule_type, 1 if admin_fee_obj else 0))

                # per provider
                # Menambahkan untuk field harga
                provider = self.env['tt.provider'].search([('code', '=', rec['provider'])]).id
                rsch_line_values = {
                    'reschedule_type': reschedule_type,
                    'reschedule_amount': total_amount,
                    'reschedule_amount_ho': total_amount,
                    'real_reschedule_amount': total_amount,
                    'admin_fee_id': admin_fee_obj.id,
                    'provider_id': provider
                }
                rsch_line_obj = self.env['tt.reschedule.line'].sudo().create(rsch_line_values)
                reschedule_line_list.append(rsch_line_obj.id)

            reschedule_obj.write({
                'reschedule_line_ids': [(6, 0, reschedule_line_list)],
                'notes': '\n'.join(note_list),
            })
            # END

            # VIN: 22/10/2020 Check klo book tetep di catet cman ledger agent tidak terpotong
            resv_obj = self.env[reschedule_obj.res_model].sudo().browse(reschedule_obj.res_id)
            if resv_obj and resv_obj.state == 'issued':
                # July 13, 2020 - SAM
                # Sementara diasumsikan untuk seluruh proses berhasil
                reschedule_obj.confirm_reschedule_from_button()
                reschedule_obj.send_reschedule_from_button()
                reschedule_obj.validate_reschedule_from_button()
                reschedule_obj.finalize_reschedule_from_button()
                reschedule_obj.action_done()
                # END
            else:
                reschedule_obj.cancel_reschedule_from_button()

            response = {
                'reschedule_id': reschedule_obj.id,
                'reschedule_number': reschedule_obj.name,
            }
            res = ERR.get_no_error(response)
            return res
        except RequestException as e:
            _logger.error('Error Update Reschedule Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Update Reschedule Airline API, %s' % traceback.format_exc())
            return ERR.get_error(500)

    def get_reschedule_airline_api(self, vals, context):
        try:
            rs_list = []
            airline_obj = self.env['tt.reservation.airline'].search([('name', '=', vals['order_number'])], limit=1)
            if airline_obj:
                for rec in airline_obj.reschedule_ids:
                    rs_list.append(rec.get_reschedule_data())
            else:
                raise RequestException(1001, additional_message="Airline reservation %s is not found in our system." % (vals['order_number']))
            return ERR.get_no_error(rs_list)
        except RequestException as e:
            _logger.error('Error Get Reschedule Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Get Reschedule Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1030)

    def to_dict_reschedule(self):
        reschedule_list = []
        for rsch in self.reschedule_ids:
            rsch_values = rsch.get_reschedule_data()
            reschedule_list.append(rsch_values)
        return  reschedule_list

    def process_update_booking_airline_api(self, vals, context):
        try:
            # print('Create Reschedule Request, %s' % json.dumps(vals))
            order_id = ''
            airline_obj = None
            if 'book_id' in vals and vals['book_id']:
                order_id = vals['book_id']
                airline_obj = self.env['tt.reservation.airline'].browse(vals['book_id'])
            elif 'order_number' in vals['order_number']:
                order_id = vals['order_number']
                airline_obj = self.env['tt.reservation.airline'].search([('name', '=', vals['order_number'])], limit=1)

            if not airline_obj:
                raise RequestException(1001, additional_message="Airline reservation %s is not found in our system." % order_id)

            resv_journey_dict = {}
            for journey in airline_obj.journey_ids:
                key = '%s%s' % (journey.origin_id.code if journey.origin_id else '', journey.destination_id.code if journey.destination_id else '')
                resv_journey_dict[key] = journey

            resv_passenger_number_dict = {}
            for psg in airline_obj.passenger_ids:
                key_number = psg.sequence
                resv_passenger_number_dict[key_number] = psg

            resv_provider_dict = {}
            for prov in airline_obj.provider_booking_ids:
                # key = prov.pnr
                key = prov.id
                resv_provider_dict[key] = prov

            # July 9, 2020 - SAM
            # Mengambil data dari gateway
            # admin_fee_obj = None
            # July 13, 2020 - SAM
            # Sementara untuk payment acquirer id diambil dari default agent id
            # payment_acquirer_obj = None
            payment_acquirer_obj = airline_obj.agent_id.default_acquirer_id
            # admin_fee_obj = self.env.ref('tt_accounting.admin_fee_reschedule')
            admin_fee_obj = None
            # END

            if vals.get('seq_id'):
                payment_acquirer_obj = self.env['payment.acquirer'].search([('seq_id', '=', vals['seq_id'])], limit=1)
            if not payment_acquirer_obj:
                return ERR.get_error(1017)
            # if not admin_fee_obj:
            #     raise Exception('Admin fee reschedule is not found, field required.')

            new_resv_obj = None
            new_provider_bookings = []
            pax_type_dict = {}
            for commit_data in vals['provider_bookings']:
                if commit_data['status'] == 'FAILED':
                    continue

                # TODO HERE NEW
                rsv_prov_obj = resv_provider_dict.get(commit_data['provider_id'], None)
                if not rsv_prov_obj:
                    raise Exception('Provider ID not found, %s' % commit_data['provider_id'])

                commit_data['passengers'] = util.match_passenger_data(commit_data['passengers'], airline_obj.passenger_ids)

                # Mendeteksi split booking
                if commit_data['pnr'] != rsv_prov_obj.pnr:
                    total_price = float(rsv_prov_obj.total_price)
                    balance_due = float(rsv_prov_obj.balance_due)
                    total_price -= float(commit_data['total_price'])
                    balance_due -= float(commit_data['balance_due'])
                    # is_same_journeys = True if len(rsv_prov_obj.journey_ids) == len(commit_data['journeys']) else False
                    # is_same_passengers = True if len(rsv_prov_obj.ticket_ids) == len(commit_data['passengers']) else False
                    new_provider_bookings.append(commit_data)
                    is_ledger_created = False
                    if any(sc_obj.is_ledger_created for sc_obj in rsv_prov_obj.cost_service_charge_ids):
                        is_ledger_created = True
                        rsv_prov_obj.action_reverse_ledger()

                    # Service Charges
                    for sc_obj in rsv_prov_obj.cost_service_charge_ids:
                        total_pax = len(commit_data['passengers'])
                        for psg in commit_data['passengers']:
                            psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                            psg_obj.write({
                                'cost_service_charge_ids': [(3, sc_obj.id)]
                            })

                        pax_count = sc_obj.pax_count - total_pax
                        if pax_count < 1:
                            sc_obj.unlink()
                        else:
                            total = pax_count * sc_obj.amount
                            sc_obj.write({
                                'pax_count': pax_count,
                                'total': total,
                            })

                    # Tickets
                    for tkt_obj in rsv_prov_obj.ticket_ids:
                        for psg in commit_data['passengers']:
                            psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                            if tkt_obj.passenger_id and tkt_obj.passenger_id.id == psg_obj.id:
                                pax_type_dict[psg_obj.id] = tkt_obj.pax_type
                                tkt_obj.unlink()
                                break

                    # Fee
                    for fee_obj in rsv_prov_obj.fee_ids:
                        for psg in commit_data['passengers']:
                            psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                            if fee_obj.passenger_id and fee_obj.passenger_id.id == psg_obj.id:
                                fee_obj.unlink()
                                break

                    # for psg_obj in airline_obj.passenger_ids:
                    #     if not any(tkt_obj.passenger_id.id == psg_obj.id for prov_obj in airline_obj.provider_booking_ids for tkt_obj in prov_obj.ticket_ids if tkt_obj.passenger_id):
                    #         psg_obj.unlink()

                    if is_ledger_created:
                        rsv_prov_obj.action_create_ledger(context['co_uid'])

                    rsv_prov_obj.write({
                        'total_price': total_price,
                        'balance_due': balance_due,
                    })
                    continue
                # TODO HERE NEW END

                # passenger_list = []
                # passenger_number_list = []
                # if commit_data['sell_reschedule']:
                #     for psg in commit_data['sell_reschedule']['passengers']:
                #         key = psg['passenger_number']
                #         if key not in resv_passenger_number_dict or key in passenger_number_list:
                #             continue
                #         passenger_list.append(resv_passenger_number_dict[key].id)
                #         passenger_number_list.append(key)
                #
                # if commit_data['ssr_journey_codes']:
                #     for ssr in commit_data['ssr_journey_codes']:
                #         for psg in ssr['sell_ssrs']:
                #             key = psg['passenger_number']
                #             if key not in resv_passenger_number_dict or key in passenger_number_list:
                #                 continue
                #             passenger_list.append(resv_passenger_number_dict[key].id)
                #             passenger_number_list.append(key)
                #
                # if commit_data['seat_segment_codes']:
                #     for seg in commit_data['seat_segment_codes']:
                #         for psg in seg['passengers']:
                #             key = psg['passenger_number']
                #             if key not in resv_passenger_number_dict or key in passenger_number_list:
                #                 continue
                #             passenger_list.append(resv_passenger_number_dict[key].id)
                #             passenger_number_list.append(key)
                #
                # # rsv_prov_obj = resv_provider_dict.get(commit_data['pnr'], None)
                # rsv_prov_obj = resv_provider_dict.get(commit_data['provider_id'], None)
                # if not rsv_prov_obj:
                #     raise Exception('Provider data not found')
                #

                total_amount = 0
                old_segment_list = []
                new_segment_list = []
                for journey in commit_data['journeys']:
                    journey_key = util.generate_journey_key_name(journey)
                    prov_journey_data = resv_journey_dict[journey_key]
                    if prov_journey_data.departure_date == journey['departure_date'] and prov_journey_data.arrival_date == journey['arrival_date']:
                        continue

                    provider_obj = rsv_prov_obj.provider_id if rsv_prov_obj else None
                    origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', journey['origin'])], limit=1)
                    destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', journey['destination'])], limit=1)
                    # Membuat data baru untuk reservasi
                    journey_values = {
                        'provider_booking_id': rsv_prov_obj.id if rsv_prov_obj else None,
                        'provider_id': provider_obj.id if provider_obj else None,
                        'pnr': commit_data['pnr'],
                        'booking_id': airline_obj.id,
                        'origin_id': origin_obj.id if origin_obj else None,
                        'destination_id': destination_obj.id if destination_obj else None,
                        'departure_date': journey['departure_date'],
                        'arrival_date': journey['arrival_date'],
                        'journey_code': journey['journey_code'],
                    }
                    n_rsv_journey_obj = self.env['tt.journey.airline'].sudo().create(journey_values)
                    for seg in journey['segments']:
                        carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', seg['carrier_code'])], limit=1)
                        origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['origin'])], limit=1)
                        destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['destination'])], limit=1)
                        n_seg_values = {
                            'segment_code': seg['segment_code'],
                            'pnr': commit_data['pnr'],
                            'fare_code': '',
                            'carrier_code': seg['carrier_code'],
                            'carrier_number': seg['carrier_number'],
                            'origin_terminal': seg['origin_terminal'],
                            'destination_terminal': seg['destination_terminal'],
                            'departure_date': seg['departure_date'],
                            'arrival_date': seg['arrival_date'],
                            'class_of_service': '',
                            'cabin_class': '',
                            'sequence': seg.get('sequence', 0),
                        }
                        if carrier_obj:
                            n_seg_values['carrier_id'] = carrier_obj.id
                        if provider_obj:
                            n_seg_values['provider_id'] = provider_obj.id
                        if origin_obj:
                            n_seg_values['origin_id'] = origin_obj.id
                        if destination_obj:
                            n_seg_values['destination_id'] = destination_obj.id

                        for fare in seg['fares']:
                            n_seg_values.update({
                                'fare_code': fare['fare_code'],
                                'class_of_service': fare['class_of_service'],
                                'cabin_class': fare['cabin_class'],
                            })
                            for sc in fare['service_charge_summary']:
                                total_amount += sc['total_price']

                        n_seg_obj = self.env['tt.segment.reschedule'].sudo().create(n_seg_values)
                        new_segment_list.append(n_seg_obj.id)

                        leg_values = {
                            'segment_id': n_seg_obj.id,
                            'origin_terminal': n_seg_values['origin_terminal'],
                            'destination_terminal': n_seg_values['destination_terminal'],
                            'departure_date': n_seg_values['departure_date'],
                            'arrival_date': n_seg_values['arrival_date'],
                        }
                        if n_seg_values.get('carrier_id'):
                            leg_values.update({
                                'carrier_id': n_seg_values['carrier_id']
                            })

                        if n_seg_values.get('provider_id'):
                            leg_values.update({
                                'provider_id': n_seg_values['provider_id']
                            })

                        if n_seg_values.get('origin_id'):
                            leg_values.update({
                                'origin_id': n_seg_values['origin_id']
                            })

                        if n_seg_values.get('destination_id'):
                            leg_values.update({
                                'destination_id': n_seg_values['destination_id']
                            })
                        self.env['tt.leg.reschedule'].sudo().create(leg_values)

                        # Membuat data baru untuk reservasi
                        n_seg_values.update({
                            'journey_id': n_rsv_journey_obj.id,
                            'provider_id': provider_obj.id if provider_obj else None,
                        })
                        n_resv_seg_obj = self.env['tt.segment.airline'].sudo().create(n_seg_values)
                        leg_values.update({
                            'segment_id': n_resv_seg_obj.id,
                            'provider_id': provider_obj.id if provider_obj else None,
                        })
                        self.env['tt.leg.airline'].sudo().create(leg_values)

                    # Menghilangkan data lama pada tt reservation airline
                    key = '{origin}{destination}'.format(**journey)
                    if key not in resv_journey_dict:
                        continue
                    resv_journey_obj = resv_journey_dict[key]
                    for seg in resv_journey_obj.segment_ids:
                        old_segment_list.append(seg.id)
                    resv_journey_obj.write({
                        'booking_id': None,
                        'provider_booking_id': None,
                    })

                # # TODO CEK DATA SSR DAN SEAT
                # for psg in commit_data['passengers']:
                #     # Fee ids di provider, nanti rencana cek code dan compare dengan passenger_id yang ada di fee ids
                #     psg_key_name = util.generate_passenger_key_name(psg)
                #     for psg_fee in psg['fees']:
                #         is_proceed = False
                #         if psg_fee['fee_type'] != 'MEAL':
                #             for fee_obj in rsv_prov_obj.fee_ids:
                #                 if psg_fee['journey_code'] == fee_obj.journey_code and psg_fee['fee_category'] == fee_obj.category:
                #                     psg_data = fee_obj.passenger_id.to_dict()
                #                     if psg_key_name in util.generate_passenger_key_name(psg_data):
                #                         is_proceed = True
                #                         fee_obj.write({
                #                             'code': psg_fee['fee_code'],
                #                             'value': psg_fee['fee_value'],
                #                             'name': psg_fee['fee_name'],
                #                             'description': json.dumps(psg_fee['description'])
                #                         })
                #
                #         if not is_proceed:
                #             passenger_id = None
                #             for tkt_obj in rsv_prov_obj.ticket_ids:
                #                 if not tkt_obj.passenger_id:
                #                     continue
                #
                #                 psg_data = tkt_obj.passenger_id.to_dict()
                #                 psg_data_key_name = util.generate_passenger_key_name(psg_data)
                #                 if psg_key_name in psg_data_key_name:
                #                     passenger_id = tkt_obj.passenger_id.id
                #
                #             rsv_prov_obj.fee_ids.create({
                #                 'name': psg_fee['fee_name'],
                #                 'code': psg_fee['fee_name'],
                #                 'category': psg_fee['fee_category'],
                #                 'description': json.dumps(psg_fee['description']),
                #                 'passenger_id': passenger_id,
                #                 'type': psg_fee['fee_type'],
                #                 'value': psg_fee['fee_value'],
                #                 'pnr': rsv_prov_obj.pnr,
                #                 'journey_code': psg_fee['journey_code'],
                #                 'provider_id': rsv_prov_obj.id,
                #             })
                # # TODO END

                total_amount = commit_data['total_price'] - rsv_prov_obj.total_price
                _logger.info('Vendor Total Price %s, Resv Total Price %s' % (commit_data['total_price'], rsv_prov_obj.total_price))
                if total_amount < 0:
                    total_amount = 0
                # total_amount -=

                # if commit_data['status'] != rsv_prov_obj.state.upper():
                #     pass
                # elif commit_data['status'] == 'ISSUED':
                #     pass
                # elif commit_data['status'] == 'BOOKED':
                #     pass

                admin_fee_obj = None
                if commit_data['status'] == 'BOOKED' and rsv_prov_obj.state == 'booked':
                    ledger_created = rsv_prov_obj.sudo().delete_service_charge()
                    if ledger_created:
                        rsv_prov_obj.action_reverse_ledger()
                        rsv_prov_obj.delete_service_charge()

                    rsv_prov_obj.sudo().delete_passenger_fees()
                    rsv_prov_obj.sudo().delete_passenger_tickets()
                    rsv_prov_obj.create_ticket_api(commit_data['passengers'], commit_data['pnr'])
                    for journey in commit_data['journeys']:
                        for segment in journey['segments']:
                            for fare in segment['fares']:
                                rsv_prov_obj.create_service_charge(fare['service_charges'])

                    rsv_prov_obj.write({
                        'total_price': commit_data['total_price'],
                        'balance_due': commit_data['balance_due'],
                        'balance_due_str': commit_data['balance_due_str'],
                    })
                elif commit_data['status'] == 'ISSUED' and rsv_prov_obj.state == 'issued':
                    admin_fee_obj = self.env.ref('tt_accounting.admin_fee_reschedule')

                if not old_segment_list and not new_segment_list:
                    continue

                res_vals = {
                    'agent_id': airline_obj.agent_id.id,
                    'customer_parent_id': airline_obj.customer_parent_id.id,
                    'booker_id': airline_obj.booker_id.id,
                    'currency_id': airline_obj.currency_id.id,
                    'service_type': airline_obj.provider_type_id.id,
                    'referenced_pnr': airline_obj.pnr,
                    'old_segment_ids': [(6, 0, old_segment_list)],
                    'new_segment_ids': [(6, 0, new_segment_list)],
                    # 'reschedule_line_ids': [(6, 0, reschedule_line_list)],
                    # 'passenger_ids': [(6, 0, passenger_list)],
                    'res_model': airline_obj._name,
                    'res_id': airline_obj.id,
                    'notes': vals.get('notes') and vals['notes'] or '',
                    'payment_acquirer_id': payment_acquirer_obj.id,
                    'created_by_api': True,
                }
                rsch_obj = self.env['tt.reschedule'].create(res_vals)

                rsch_line_values = {
                    'reschedule_type': 'reschedule',
                    'reschedule_amount': total_amount,
                    'reschedule_amount_ho': total_amount,
                    'real_reschedule_amount': total_amount,
                    'reschedule_id': rsch_obj.id
                }
                if admin_fee_obj:
                    rsch_line_values.update({
                        'admin_fee_id': admin_fee_obj.id
                    })
                rsch_line_obj = self.env['tt.reschedule.line'].sudo().create(rsch_line_values)
                # END

                # VIN: 22/10/2020 Check klo book tetep di catet cman ledger agent tidak terpotong
                if rsv_prov_obj.state == 'issued':
                    # July 13, 2020 - SAM
                    # Sementara diasumsikan untuk seluruh proses berhasil
                    rsch_obj.confirm_reschedule_from_button()
                    rsch_obj.send_reschedule_from_button()
                    rsch_obj.validate_reschedule_from_button()
                    rsch_obj.finalize_reschedule_from_button()
                    # reschedule_obj.action_done()
                    # END
                else:
                    rsch_obj.cancel_reschedule_from_button()

            # Remove passenger from list
            # Get New Data
            if 'book_id' in vals and vals['book_id']:
                airline_obj = self.env['tt.reservation.airline'].browse(vals['book_id'])
            elif 'order_number' in vals['order_number']:
                airline_obj = self.env['tt.reservation.airline'].search([('name', '=', vals['order_number'])], limit=1)

            # Split Booking
            if new_provider_bookings:
                airline_obj.write({
                    'split_uid': self.env.user.id,
                    'split_date': fields.Datetime.now(),
                })

                dest_obj = self.env['tt.destinations']
                provider_type_id = self.env.ref('tt_reservation_airline.tt_provider_type_airline')

                origin_code = ''
                departure_date = ''
                destination_code = ''
                arrival_date = ''
                passenger_airline_ids = []
                adult = 0
                child = 0
                infant = 0
                passenger_id_dict = {}
                for rec in new_provider_bookings:
                    for journey in rec['journeys']:
                        if not origin_code:
                            origin_code = journey['origin']
                            destination_code = journey['destination']
                            departure_date = journey['departure_date']
                        elif destination_code and origin_code != journey['destination']:
                            destination_code = journey['destination']
                        arrival_date = journey['arrival_date']

                    for psg in rec['passengers']:
                        if psg['passenger_id'] in passenger_id_dict:
                            continue

                        psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                        n_psg_val = psg_obj.to_dict()
                        n_psg_obj = self.env['tt.reservation.passenger.airline'].create(n_psg_val)
                        passenger_id_dict[psg['passenger_id']] = n_psg_obj.id
                        psg.update({
                            'passenger_id': n_psg_obj.id
                        })
                        passenger_airline_ids.append((4, n_psg_obj.id))
                        if psg['pax_type'] in ['ADT', 'YCD']:
                            adult += 1
                        elif psg['pax_type'] == 'CHD':
                            child += 1
                        elif psg['pax_type'] == 'INF':
                            infant += 1

                origin_id = dest_obj.get_id(origin_code, provider_type_id)
                destination_id = dest_obj.get_id(destination_code, provider_type_id)

                new_vals = {
                    'split_from_resv_id': airline_obj.id,
                    'split_uid': self.env.user.id,
                    'split_date': fields.Datetime.now(),
                    # 'pnr': ','.join(pnr_list),
                    'agent_id': airline_obj.agent_id and airline_obj.agent_id.id or False,
                    'customer_parent_id': airline_obj.customer_parent_id and airline_obj.customer_parent_id.id or False,
                    'provider_type_id': airline_obj.provider_type_id.id,
                    # 'provider_name': airline_obj.provider_name,
                    # 'carrier_name': airline_obj.carrier_name,
                    # 'hold_date': book_obj.hold_date,
                    'user_id': airline_obj.user_id and airline_obj.user_id.id or False,
                    # 'create_date': book_obj.create_date,
                    # 'booked_uid': book_obj.booked_uid and book_obj.booked_uid.id or False,
                    # 'booked_date': book_obj.booked_date,
                    # 'issued_uid': book_obj.issued_uid and book_obj.issued_uid.id or False,
                    # 'issued_date': datetime.now(),
                    'origin_id': origin_id and origin_id or False,
                    'destination_id': destination_id and destination_id or False,
                    'sector_type': airline_obj.sector_type,
                    'direction': airline_obj.direction,
                    'departure_date': departure_date and departure_date or '',
                    'arrival_date': arrival_date and arrival_date or '',
                    'booker_id': airline_obj.booker_id and airline_obj.booker_id.id or False,
                    'contact_id': airline_obj.contact_id and airline_obj.contact_id.id or False,
                    'contact_title': airline_obj.contact_title,
                    'contact_email': airline_obj.contact_email,
                    'contact_phone': airline_obj.contact_phone,
                    'passenger_ids': passenger_airline_ids,
                    'adult': adult,
                    'child': child,
                    'infant': infant,
                    # 'is_invoice_created': book_obj.is_invoice_created,
                    # 'state': book_obj.state
                }

                new_resv_obj = self.env['tt.reservation.airline'].create(new_vals)
                provider_ids, name_ids = new_resv_obj._create_provider_api(new_provider_bookings, context)

                new_resv_obj.calculate_service_charge()
                new_resv_obj.check_provider_state(context)

                new_resv_obj.write({
                    'provider_name': ','.join(name_ids['provider']),
                    'carrier_name': ','.join(name_ids['carrier']),
                })

                self.env.cr.commit()
                for rec in new_provider_bookings:
                    for prov_obj in new_resv_obj.provider_booking_ids:
                        if prov_obj.pnr == rec['pnr']:
                            if 'sell_reschedule' in rec:
                                rec.pop('sell_reschedule')
                            rec.update({
                                'provider_id': prov_obj.id
                            })
                            for journey in rec['journeys']:
                                for seg in journey['segments']:
                                    fare_obj = seg['fares'][0]
                                    seg.update({
                                        'class_of_service': fare_obj['class_of_service'],
                                        'cabin_class': fare_obj['cabin_class'],
                                        'fare_code': fare_obj['fare_code'],
                                    })
                            break

                new_payload = {
                    'book_id': new_resv_obj.id,
                    'order_number': new_resv_obj.name,
                    'provider_bookings': new_provider_bookings,
                }
                self.env['tt.reservation.airline'].update_pnr_provider_airline_api(new_payload, context)
                for prov in new_resv_obj.provider_booking_ids:
                    if prov.state == 'issued':
                        prov.action_create_ledger(new_resv_obj.issued_uid.id)

                # for rec in new_provider_bookings:
                #     rsv_prov_obj = resv_provider_dict.get(rec['provider_id'], None)
                #     # is_same_journeys = True if len(rsv_prov_obj.journey_ids) == len(rec['journeys']) else False
                #     is_same_passengers = True if len(rsv_prov_obj.ticket_ids) == len(rec['passengers']) else False

            adult = airline_obj.adult
            child = airline_obj.child
            infant = airline_obj.infant
            for psg_obj in airline_obj.passenger_ids:
                if not any(psg_obj.id == tkt_obj.passenger_id.id for prov_obj in airline_obj.provider_booking_ids for tkt_obj in prov_obj.ticket_ids if tkt_obj.passenger_id):
                    pax_type = pax_type_dict[psg_obj.id]
                    if pax_type in ['ADT', 'YCD']:
                        adult -= 1
                    elif pax_type == 'CHD':
                        child -= 1
                    elif pax_type == 'INF':
                        infant -= 1
                    psg_obj.unlink()

            airline_obj.write({
                'adult': adult,
                'child': child,
                'infant': infant,
                'departure_date': airline_obj.journey_ids[0].departure_date,
            })
            airline_obj.calculate_service_charge()
            airline_obj.check_provider_state(context)
            for prov_obj in airline_obj.provider_booking_ids:
                prov_obj.write({
                    'departure_date': prov_obj.journey_ids[0].departure_date,
                    'arrival_date': prov_obj.journey_ids[-1].arrival_date,
                })
            payload = {
                'order_number': airline_obj.name if not new_resv_obj else new_resv_obj.name
            }
            return ERR.get_no_error(payload)
        except RequestException as e:
            _logger.error('Error Create Reschedule Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Create Reschedule Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1030)

