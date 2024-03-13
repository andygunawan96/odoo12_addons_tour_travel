from odoo import api,models,fields, _
from ...tools.ERR import RequestException
from ...tools import util,variables,ERR
import logging,traceback
import json
from threading import Thread
from ...tools.db_connector import GatewayConnector
from datetime import datetime
import copy


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

                if vals.get('acquirer_seq_id'):
                    payment_acquirer_obj = self.env['payment.acquirer'].search([('seq_id', '=', vals['acquirer_seq_id'])], limit=1)
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
                                carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', seg['carrier_code']), ('provider_type_id', '=', airline_obj.provider_type_id.id)], limit=1)
                                provider_obj = self.env['tt.provider'].sudo().search([('code', '=', seg['provider']), ('provider_type_id', '=', airline_obj.provider_type_id.id)], limit=1)
                                origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['origin']), ('provider_type_id', '=', airline_obj.provider_type_id.id)], limit=1)
                                destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['destination']), ('provider_type_id', '=', airline_obj.provider_type_id.id)], limit=1)
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
                                    'status': seg.get('status', ''),
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
                            'status': seg.status,
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
                    'ho_id': airline_obj.ho_id.id,
                    'customer_parent_id': airline_obj.customer_parent_id.id,
                    'booker_id': airline_obj.booker_id.id,
                    'currency_id': airline_obj.currency_id.id,
                    'service_type': airline_obj.provider_type_id.id,
                    'referenced_pnr': airline_obj.pnr,
                    'referenced_document': airline_obj.name,
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

                for rsch_pax in res_obj.passenger_ids:
                    # fill RS number to pax's reschedule CSCs with empty description
                    for rsch_p_csc in rsch_pax.channel_service_charge_ids.filtered(lambda x: 'rs' in x.charge_code.split('.')):
                        if not rsch_p_csc.description:
                            rsch_p_csc.update({
                                'description': res_obj.name
                            })

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

                provider_type_id = reschedule_obj.provider_type_id and reschedule_obj.provider_type_id.id or False
                customer_parent_id = reschedule_obj.customer_parent_id and reschedule_obj.customer_parent_id.id or False
                admin_fee_obj = self.env['tt.reschedule'].get_reschedule_admin_fee_rule(reschedule_obj.agent_id.id, customer_parent_id=customer_parent_id, provider_type_id=provider_type_id)
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
                reschedule_obj.confirm_reschedule_from_api(context.get('co_uid'))
                reschedule_obj.send_reschedule_from_button()
                agent_payment_method = 'balance'
                if vals.get('agent_payment_method'):
                    agent_payment_method = vals['agent_payment_method']
                reschedule_obj.validate_reschedule_from_button(agent_payment_method)
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
        return reschedule_list

    def process_update_booking_airline_api(self, vals, context):
        try:
            # print('Create Reschedule Request, %s' % json.dumps(vals))
            # June 9, 2021 - SAM
            # Mengubah co uid context menjadi co uid sistem
            if 'use_system_user' in vals and vals['use_system_user']:
                context.update({
                    'co_uid': self.env.uid
                })
            # END

            # January 20, 2022 - SAM
            is_webhook = vals['is_webhook'] if 'is_webhook' in vals else False
            reschedule_date = datetime.now()
            reschedule_uid = context['co_uid']
            # END

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

            # hapus ticket ori
            for ticket_ori in airline_obj.printout_ticket_original_ids:
                ticket_ori.active = False
            # hapus ticket yg sudah ada
            if airline_obj.printout_ticket_id:
                airline_obj.printout_ticket_id.unlink()
            if airline_obj.printout_ticket_price_id:
                airline_obj.printout_ticket_price_id.unlink()
            if airline_obj.printout_ticket_price_id:
                airline_obj.printout_ticket_price_id.unlink()
            if airline_obj.printout_ho_invoice_id:
                airline_obj.printout_ho_invoice_id.unlink()
            if airline_obj.printout_vendor_invoice_id:
                airline_obj.printout_vendor_invoice_id.unlink()

            resv_journey_dict = {}
            resv_segment_dict = {}
            resv_segment_journey_dict = {}
            for journey in airline_obj.journey_ids:
                key = '%s-%s' % (journey.origin_id.code if journey.origin_id else '', journey.destination_id.code if journey.destination_id else '')
                resv_journey_dict[key] = journey
                for seg in journey.segment_ids:
                    origin = seg.origin_id.code if seg.origin_id else ''
                    destination = seg.destination_id.code if seg.destination_id else ''
                    seg_key = '%s-%s' % (origin, destination)
                    resv_segment_dict[seg_key] = seg
                    resv_segment_journey_dict[seg_key] = journey

            resv_passenger_number_dict = {}
            for psg in airline_obj.passenger_ids:
                key_number = psg.sequence
                resv_passenger_number_dict[key_number] = psg

            resv_provider_dict = {}
            for prov in airline_obj.provider_booking_ids:
                # key = prov.pnr
                key = prov.id
                resv_provider_dict[key] = prov

            is_admin_charge = True
            if 'is_admin_charge' in vals:
                is_admin_charge = vals['is_admin_charge']

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

            if vals.get('acquirer_seq_id'):
                payment_acquirer_obj = self.env['payment.acquirer'].search([('seq_id', '=', vals['acquirer_seq_id'])], limit=1)
            # if not payment_acquirer_obj: #BOOKED TIDAK KIRIM seq_id
            #     return ERR.get_error(1017)
            # if not admin_fee_obj:
            #     raise Exception('Admin fee reschedule is not found, field required.')

            new_resv_obj = None
            new_provider_bookings = []
            pax_type_dict = {}
            for commit_data in vals['provider_bookings']:
                if commit_data['status'] == 'FAILED':
                    if 'reschedule_id' in commit_data:
                        rsch_obj = self.env['tt.reschedule'].browse(commit_data['reschedule_id'])
                        rsch_obj.write({
                            'notes': commit_data.get('error_msg', '')
                        })
                    continue

                # TODO HERE NEW
                rsv_prov_obj = resv_provider_dict.get(commit_data['provider_id'], None)
                if not rsv_prov_obj:
                    raise Exception('Provider ID not found, %s' % commit_data['provider_id'])

                rsv_prov_pax_count_dict = {
                    'ADT': 0,
                    'CHD': 0,
                    'INF': 0,
                    'YCD': 0,
                }

                # July 14, 2023 - SAM
                provider_values = rsv_prov_obj.set_provider_detail_info(commit_data)

                ## 25 jul 2023 - IVAN pop agar pnr awal tidak berubah, agar bisa detect split
                provider_values.pop('pnr')
                provider_values.pop('pnr2')
                ## end
                rsv_prov_obj.write(provider_values)
                # END

                for tkt_obj in rsv_prov_obj.ticket_ids:
                    pax_type = tkt_obj.pax_type
                    if pax_type not in rsv_prov_pax_count_dict:
                        rsv_prov_pax_count_dict[pax_type] = 0
                    rsv_prov_pax_count_dict[pax_type] += 1

                commit_data['passengers'] = util.match_passenger_data(commit_data['passengers'], airline_obj.passenger_ids)

                # Mendeteksi split booking
                if commit_data['pnr'] != rsv_prov_obj.pnr:
                    total_price = float(rsv_prov_obj.total_price)
                    balance_due = float(rsv_prov_obj.balance_due)
                    total_price -= float(commit_data['total_price'])
                    balance_due -= float(commit_data['balance_due'])

                    # April 6, 2022 - SAM
                    # Untuk trigger update harga apabila split booking BOOKED
                    if commit_data['status'] == "BOOKED":
                        total_price += 1
                        commit_data['total_price'] = float(commit_data['total_price']) + 1
                    # END

                    # is_same_journeys = True if len(rsv_prov_obj.journey_ids) == len(commit_data['journeys']) else False
                    # is_same_passengers = True if len(rsv_prov_obj.ticket_ids) == len(commit_data['passengers']) else False
                    new_provider_bookings.append(commit_data)
                    is_ledger_created = False
                    if any(sc_obj.is_ledger_created for sc_obj in rsv_prov_obj.cost_service_charge_ids):
                        is_ledger_created = True
                        rsv_prov_obj.action_reverse_ledger()

                    # April 5, 2022 - SAM
                    # Menghitung jumlah pax count pada pax type yang ada
                    pax_count_dict = {
                        'ADT': 0,
                        'CHD': 0,
                        'INF': 0,
                        'YCD': 0,
                    }
                    prov_psg_id_list = []
                    prov_psg_number_list = []
                    for pax in commit_data['passengers']:
                        psg_id = pax.get('passenger_id', '')
                        psg_number = pax['passenger_number']
                        prov_psg_id_list.append(psg_id)
                        prov_psg_number_list.append(psg_number)
                        pax_type = pax['pax_type']
                        if pax_type not in pax_count_dict:
                            pax_count_dict[pax_type] = 0
                        pax_count_dict[pax_type] += 1

                        # 27 Jul 2023 CSC
                        for pax_obj in rsv_prov_obj.booking_id.passenger_ids:
                            if pax_obj.id == psg_id and pax_obj.channel_service_charge_ids:
                                pax['upsell'] = []
                                for csc_obj in pax_obj.channel_service_charge_ids:
                                    pax['upsell'].append({
                                        "charge_code": csc_obj.charge_code,
                                        "charge_type": csc_obj.charge_type,
                                        "currency": csc_obj.currency_id.name,
                                        "amount": csc_obj.amount
                                    })


                    # END

                    # Service Charges
                    for sc_obj in rsv_prov_obj.cost_service_charge_ids:
                        # April 5, 2022 - SAM
                        # total_pax = len(commit_data['passengers'])
                        sc_pax_type = sc_obj.pax_type
                        if sc_pax_type not in pax_count_dict:
                            continue
                        total_pax = pax_count_dict[sc_pax_type]
                        if total_pax < 1:
                            continue
                        # END
                        for psg in commit_data['passengers']:
                            psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                            psg_obj.write({
                                'cost_service_charge_ids': [(3, sc_obj.id)]
                            })
                        # April 5, 2022 - SAM
                        try:
                            if sc_obj.charge_type in ['ROC', 'RAC', 'DISC']:
                                # Memindahkan service charge ke pax lain dalam 1 rerservasi
                                # Apabila tidak ada yang bisa dipindahkan, baru akan di pindah ke reservasi yang baru
                                is_assigned = False
                                if sc_obj.pax_count == 1:
                                    for tkt_obj in rsv_prov_obj.ticket_ids:
                                        if sc_obj.pax_type != tkt_obj.pax_type:
                                            continue
                                        if not tkt_obj.passenger_id:
                                            continue
                                        if tkt_obj.passenger_id.id in prov_psg_id_list:
                                            continue

                                        tkt_obj.passenger_id.write({
                                            'cost_service_charge_ids': [(4, sc_obj.id)]
                                        })
                                        is_assigned = True
                                        break

                                if is_assigned:
                                    continue

                                sc_values = sc_obj.to_dict()
                                if sc_obj.commission_agent_id:
                                    sc_values.update({
                                        'commission_agent_id': sc_obj.commission_agent_id.id
                                    })
                                sc_total = sc_values['amount'] * total_pax
                                sc_values.update({
                                    'pax_count': total_pax,
                                    'total': sc_total
                                })
                                if sc_obj.charge_code != 'disc_voucher': ## disc_voucher tidak tercopy jika split, split delete voucher
                                    commit_data['journeys'][-1]['segments'][-1]['fares'][-1]['service_charges'].append(sc_values)
                        except:
                            _logger.error('Failed to append service charges, %s' % traceback.format_exc())
                        # END

                        pax_count = sc_obj.pax_count - total_pax
                        if pax_count < 1:
                            sc_obj.sudo().unlink()
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
                                tkt_obj.sudo().unlink()
                                break

                    # Fee
                    for fee_obj in rsv_prov_obj.fee_ids:
                        for psg in commit_data['passengers']:
                            psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                            if fee_obj.passenger_id and fee_obj.passenger_id.id == psg_obj.id:
                                fee_obj.sudo().unlink()
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

                # October 20, 2021 - SAM
                passenger_list = []
                for psg in commit_data['passengers']:
                    passenger_list.append(psg['passenger_id'])
                # END

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

                # total_amount = 0
                old_segment_list = []
                new_segment_list = []
                # July 1, 2021 - SAM
                # Update mekanisme pengecekkan by segment (karena vendor tidak standard memberikan info journey)

                # # journey_key_list = [key for key in resv_journey_dict.keys()]
                # # journey_key_list_str = ';'.join(journey_key_list)
                # for journey in commit_data['journeys']:
                #     journey_key = util.generate_journey_key_name(journey)
                #     # if journey_key not in resv_journey_dict:
                #     #     _logger.error('Journey key %s not found, key in list %s' % (journey_key, journey_key_list_str))
                #     #     continue
                #
                #     prov_journey_data = resv_journey_dict[journey_key]
                #     if prov_journey_data.departure_date == journey['departure_date'] and prov_journey_data.arrival_date == journey['arrival_date']:
                #         continue
                #
                #     provider_obj = rsv_prov_obj.provider_id if rsv_prov_obj else None
                #     origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', journey['origin'])], limit=1)
                #     destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', journey['destination'])], limit=1)
                #     # Membuat data baru untuk reservasi
                #     journey_values = {
                #         'provider_booking_id': rsv_prov_obj.id if rsv_prov_obj else None,
                #         'provider_id': provider_obj.id if provider_obj else None,
                #         'pnr': commit_data['pnr'],
                #         'booking_id': airline_obj.id,
                #         'origin_id': origin_obj.id if origin_obj else None,
                #         'destination_id': destination_obj.id if destination_obj else None,
                #         'departure_date': journey['departure_date'],
                #         'arrival_date': journey['arrival_date'],
                #         'journey_code': journey['journey_code'],
                #     }
                #     n_rsv_journey_obj = self.env['tt.journey.airline'].sudo().create(journey_values)
                #     for seg in journey['segments']:
                #         carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', seg['carrier_code'])], limit=1)
                #         origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['origin'])], limit=1)
                #         destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['destination'])], limit=1)
                #         n_seg_values = {
                #             'segment_code': seg['segment_code'],
                #             'pnr': commit_data['pnr'],
                #             'fare_code': '',
                #             'carrier_code': seg['carrier_code'],
                #             'carrier_number': seg['carrier_number'],
                #             'origin_terminal': seg['origin_terminal'],
                #             'destination_terminal': seg['destination_terminal'],
                #             'departure_date': seg['departure_date'],
                #             'arrival_date': seg['arrival_date'],
                #             'class_of_service': '',
                #             'cabin_class': '',
                #             'sequence': seg.get('sequence', 0),
                #         }
                #         if carrier_obj:
                #             n_seg_values['carrier_id'] = carrier_obj.id
                #         if provider_obj:
                #             n_seg_values['provider_id'] = provider_obj.id
                #         if origin_obj:
                #             n_seg_values['origin_id'] = origin_obj.id
                #         if destination_obj:
                #             n_seg_values['destination_id'] = destination_obj.id
                #
                #         for fare in seg['fares']:
                #             n_seg_values.update({
                #                 'fare_code': fare['fare_code'],
                #                 'class_of_service': fare['class_of_service'],
                #                 'cabin_class': fare['cabin_class'],
                #             })
                #             # for sc in fare['service_charge_summary']:
                #             #     total_amount += sc['total_price']
                #
                #         n_seg_obj = self.env['tt.segment.reschedule'].sudo().create(n_seg_values)
                #         new_segment_list.append(n_seg_obj.id)
                #
                #         leg_values = {
                #             'segment_id': n_seg_obj.id,
                #             'origin_terminal': n_seg_values['origin_terminal'],
                #             'destination_terminal': n_seg_values['destination_terminal'],
                #             'departure_date': n_seg_values['departure_date'],
                #             'arrival_date': n_seg_values['arrival_date'],
                #         }
                #         if n_seg_values.get('carrier_id'):
                #             leg_values.update({
                #                 'carrier_id': n_seg_values['carrier_id']
                #             })
                #
                #         if n_seg_values.get('provider_id'):
                #             leg_values.update({
                #                 'provider_id': n_seg_values['provider_id']
                #             })
                #
                #         if n_seg_values.get('origin_id'):
                #             leg_values.update({
                #                 'origin_id': n_seg_values['origin_id']
                #             })
                #
                #         if n_seg_values.get('destination_id'):
                #             leg_values.update({
                #                 'destination_id': n_seg_values['destination_id']
                #             })
                #         self.env['tt.leg.reschedule'].sudo().create(leg_values)
                #
                #         # Membuat data baru untuk reservasi
                #         n_seg_values.update({
                #             'journey_id': n_rsv_journey_obj.id,
                #             'provider_id': provider_obj.id if provider_obj else None,
                #         })
                #         n_resv_seg_obj = self.env['tt.segment.airline'].sudo().create(n_seg_values)
                #         leg_values.update({
                #             'segment_id': n_resv_seg_obj.id,
                #             'provider_id': provider_obj.id if provider_obj else None,
                #         })
                #         self.env['tt.leg.airline'].sudo().create(leg_values)
                #
                #     # Menghilangkan data lama pada tt reservation airline
                #     key = '{origin}{destination}'.format(**journey)
                #     if key not in resv_journey_dict:
                #         continue
                #     resv_journey_obj = resv_journey_dict[key]
                #     for seg in resv_journey_obj.segment_ids:
                #         old_segment_list.append(seg.id)
                #     resv_journey_obj.write({
                #         'booking_id': None,
                #         'provider_booking_id': None,
                #     })

                # New
                # resv_segment_str = ';'.join([key for key in resv_segment_dict.keys()])
                # for journey in commit_data['journeys']:
                #     orig_segment = journey['segments'][0]
                #     dest_segment = journey['segments'][-1]
                #     journey_key = '%s-%s' % (orig_segment['origin'], dest_segment['destination'])
                #     if 'journey_key' in journey and journey['journey_key']:
                #         journey_key = journey['journey_key']
                #
                #     check_journey_level = True
                #     if journey_key not in resv_journey_dict:
                #         _logger.error('Journey not found %s, journey list in data %s' % (journey_key, resv_segment_str))
                #         check_journey_level = False
                #         continue
                #
                #     journey_prov_data = resv_journey_dict[journey_key]
                #     commit_segment_total = len(journey['segments'])
                #     prov_data_segment_total = len(journey_prov_data.segment_ids)
                #
                #     # September 15, 2022 - SAM
                #     # Menambahkan pengecekkan
                #     is_same_departure = True if journey_prov_data.departure_date == orig_segment['departure_date'] else False
                #     is_same_arrival = True if journey_prov_data.arrival_date == dest_segment['arrival_date'] else False
                #     is_same_segment_total = True if commit_segment_total == prov_data_segment_total else False
                #     is_same_class_of_service = False
                #     is_same_fare_basis_code = False
                #     try:
                #         if is_same_segment_total:
                #             class_of_service_flag_list = []
                #             fare_basis_code_flag_list = []
                #             for seg_idx, seg_obj in enumerate(journey_prov_data.segment_ids):
                #                 seg_data = journey['segments'][seg_idx]
                #                 for fare in seg_data.get('fares', []):
                #                     fare_cos = fare.get('class_of_service', '')
                #                     fare_fbc = fare.get('fare_basis_code', '')
                #                     if seg_obj.class_of_service == fare_cos:
                #                         class_of_service_flag_list.append(True)
                #                     else:
                #                         class_of_service_flag_list.append(False)
                #                     if seg_obj.fare_basis_code == fare_fbc:
                #                         fare_basis_code_flag_list.append(True)
                #                     else:
                #                         fare_basis_code_flag_list.append(False)
                #
                #             if class_of_service_flag_list and all(flag == True for flag in class_of_service_flag_list):
                #                 is_same_class_of_service = True
                #             if fare_basis_code_flag_list and all(flag == True for flag in fare_basis_code_flag_list):
                #                 is_same_fare_basis_code = True
                #     except:
                #         _logger.error('Error compare class of service in segments')
                #     # END
                #
                #     # if journey_prov_data.departure_date == orig_segment['departure_date'] and journey_prov_data.arrival_date == dest_segment['arrival_date']:
                #     #     if commit_segment_total == prov_data_segment_total:
                #     #         continue
                #
                #     if is_same_departure and is_same_arrival and is_same_segment_total and is_same_class_of_service and is_same_fare_basis_code:
                #         continue
                #
                #     for seg_obj in journey_prov_data.segment_ids:
                #         seg_obj.write({
                #             'journey_id': None
                #         })
                #         old_segment_list.append(seg_obj.id)
                #
                #     for seg in journey['segments']:
                #         # seg_key = '{origin}-{destination}'.format(**seg)
                #         # if seg_key not in resv_segment_dict:
                #         #     _logger.error('Segment not found %s, segment list in data %s' % (seg_key, resv_segment_str))
                #         #     continue
                #         #
                #         # prov_segment_data = resv_segment_dict[seg_key]
                #         # if prov_segment_data.departure_date == seg['departure_date'] and prov_segment_data.arrival_date == seg['arrival_date']:
                #         #     continue
                #
                #         provider_obj = rsv_prov_obj.provider_id if rsv_prov_obj else None
                #         carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', seg['carrier_code'])], limit=1)
                #         origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['origin'])], limit=1)
                #         destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['destination'])], limit=1)
                #         n_seg_values = {
                #             'segment_code': seg['segment_code'],
                #             'pnr': commit_data['pnr'],
                #             'fare_code': '',
                #             'carrier_code': seg['carrier_code'],
                #             'carrier_number': seg['carrier_number'],
                #             'origin_terminal': seg['origin_terminal'],
                #             'destination_terminal': seg['destination_terminal'],
                #             'departure_date': seg['departure_date'],
                #             'arrival_date': seg['arrival_date'],
                #             'class_of_service': '',
                #             'cabin_class': '',
                #             'sequence': seg.get('sequence', 0),
                #         }
                #         if carrier_obj:
                #             n_seg_values['carrier_id'] = carrier_obj.id
                #         if provider_obj:
                #             n_seg_values['provider_id'] = provider_obj.id
                #         if origin_obj:
                #             n_seg_values['origin_id'] = origin_obj.id
                #         if destination_obj:
                #             n_seg_values['destination_id'] = destination_obj.id
                #
                #         for fare in seg['fares']:
                #             n_seg_values.update({
                #                 'fare_code': fare['fare_code'],
                #                 'class_of_service': fare['class_of_service'],
                #                 'cabin_class': fare['cabin_class'],
                #             })
                #             # for sc in fare['service_charge_summary']:
                #             #     total_amount += sc['total_price']
                #
                #         n_seg_obj = self.env['tt.segment.reschedule'].sudo().create(n_seg_values)
                #         new_segment_list.append(n_seg_obj.id)
                #
                #         leg_values = {
                #             'segment_id': n_seg_obj.id,
                #             'origin_terminal': n_seg_values['origin_terminal'],
                #             'destination_terminal': n_seg_values['destination_terminal'],
                #             'departure_date': n_seg_values['departure_date'],
                #             'arrival_date': n_seg_values['arrival_date'],
                #         }
                #         if n_seg_values.get('carrier_id'):
                #             leg_values.update({
                #                 'carrier_id': n_seg_values['carrier_id']
                #             })
                #
                #         if n_seg_values.get('provider_id'):
                #             leg_values.update({
                #                 'provider_id': n_seg_values['provider_id']
                #             })
                #
                #         if n_seg_values.get('origin_id'):
                #             leg_values.update({
                #                 'origin_id': n_seg_values['origin_id']
                #             })
                #
                #         if n_seg_values.get('destination_id'):
                #             leg_values.update({
                #                 'destination_id': n_seg_values['destination_id']
                #             })
                #         self.env['tt.leg.reschedule'].sudo().create(leg_values)
                #
                #         # Membuat data baru untuk reservasi
                #         n_seg_values.update({
                #             'provider_id': provider_obj.id if provider_obj else None,
                #             'journey_id': journey_prov_data.id,
                #         })
                #         n_resv_seg_obj = self.env['tt.segment.airline'].sudo().create(n_seg_values)
                #         leg_values.update({
                #             'segment_id': n_resv_seg_obj.id,
                #             'provider_id': provider_obj.id if provider_obj else None,
                #         })
                #         self.env['tt.leg.airline'].sudo().create(leg_values)
                #
                #         # Menghilangkan data lama pada tt reservation airline
                #         # prov_segment_data.write({
                #         #     'journey_id': None
                #         # })
                #         # old_segment_list.append(prov_segment_data.id)
                #
                #     if journey_prov_data.is_vtl_flight != journey.get('is_vtl_flight', False):
                #         journey_prov_data.write({
                #             'is_vtl_flight': journey['is_vtl_flight']
                #         })
                # New End

                # September 22, 2022 - SAM
                # journey_key_list = []
                # for journey in commit_data['journeys']:
                #     orig_segment = journey['segments'][0]
                #     dest_segment = journey['segments'][-1]
                #     journey_key = '%s-%s' % (orig_segment['origin'], dest_segment['destination'])
                #     if 'journey_key' in journey and journey['journey_key']:
                #         journey_key = journey['journey_key']
                #     journey_key_list.append(journey_key)
                #
                # if all(jk in resv_journey_dict for jk in journey_key_list):
                #     is_same_journeys = True
                # else:
                #     is_same_journeys = False

                # August 7, 2023 - SAM
                # Sementara untuk flow perubahan jadwal akan mengganti struktur journeys nya apabila ada perbedaan
                # Antisipasi untuk struktur journey dari SIA yang dapat berubah
                # Kemungkinan karena pengaruh fare class nya juga yang dapat berubah dari sisi SQ
                # Kalau tidak diubah, akan pengaruh ke reschedule nya
                # Contoh :
                # Data Awal
                # Journey 1 : SUB - SIN - MEL
                # Menjadi
                # Journey 1 : SUB - SIN
                # Joruney 2 : SIN - MEL
                prov_segment_key_list = []
                prov_journey_count = 0
                prov_departure_date_list = []
                prov_arrival_date_list = []
                prov_class_of_service_list = []
                prov_fare_basis_code_list = []
                for prov_journey_obj in rsv_prov_obj.journey_ids:
                    prov_journey_count += 1
                    for prov_seg_obj in prov_journey_obj.segment_ids:
                        origin = prov_seg_obj.origin_id.code if prov_seg_obj.origin_id else ''
                        destination = prov_seg_obj.destination_id.code if prov_seg_obj.destination_id else ''
                        key = '%s-%s' % (origin, destination)
                        prov_segment_key_list.append(key)

                        cos = prov_seg_obj.class_of_service if prov_seg_obj.class_of_service else ''
                        prov_class_of_service_list.append(cos)
                        fbs = prov_seg_obj.fare_basis_code if prov_seg_obj.fare_basis_code else ''
                        prov_fare_basis_code_list.append(fbs)

                        dep_date = prov_seg_obj.departure_date if prov_seg_obj.departure_date else ''
                        prov_departure_date_list.append(dep_date)
                        arr_date = prov_seg_obj.arrival_date if prov_seg_obj.arrival_date else ''
                        prov_arrival_date_list.append(arr_date)

                com_segment_key_list = []
                is_structure_valid = True
                com_journey_count = 0
                com_departure_date_list = []
                com_arrival_date_list = []
                com_class_of_service_list = []
                com_fare_basis_code_list = []
                for journey in commit_data.get('journeys', []):
                    com_journey_count += 1
                    segments = journey.get('segments', [])
                    if segments:
                        if segments[0].get('origin', '') == segments[-1].get('destination', ''):
                            is_structure_valid = False
                    for seg in segments:
                        origin = seg['origin'] if seg.get('origin') else ''
                        destination = seg['destination'] if seg.get('destination') else ''
                        key = '%s-%s' % (origin, destination)
                        com_segment_key_list.append(key)

                        dep_date = seg['departure_date'] if seg.get('departure_date') else ''
                        com_departure_date_list.append(dep_date)
                        arr_date = seg['arrival_date'] if seg.get('arrival_date') else ''
                        com_arrival_date_list.append(arr_date)

                        for fare in seg.get('fares', []):
                            cos = fare['class_of_service'] if fare.get('class_of_service') else ''
                            com_class_of_service_list.append(cos)
                            fbs = fare['fare_basis_code'] if fare.get('fare_basis_code') else ''
                            com_fare_basis_code_list.append(fbs)

                # if is_structure_valid:
                #     print('### HERE : structure valid')
                # else:
                #     print('### HERE : structure not valid')

                if sorted(prov_segment_key_list) == sorted(com_segment_key_list):
                    is_same_journeys = True
                    # print('### HERE : same journeys')
                else:
                    # print('### HERE : not same journeys')
                    is_same_journeys = False

                if prov_journey_count == com_journey_count:
                    # print('### HERE : journey count same, %s' % prov_journey_count)
                    is_same_journey_count = True
                else:
                    # print('### HERE : journey count not same, prov %s, com %s' % (prov_journey_count, com_journey_count))
                    is_same_journey_count = False

                if sorted(prov_departure_date_list) == sorted(com_departure_date_list):
                    is_same_departure = True
                    # print('### HERE : same depart')
                else:
                    is_same_departure = False
                    # print('### HERE : not same depart')

                if sorted(prov_arrival_date_list) == sorted(com_arrival_date_list):
                    is_same_arrival = True
                    # print('### HERE : same arrival')
                else:
                    is_same_arrival = False
                    # print('### HERE : not same arrival')

                if sorted(prov_class_of_service_list) == sorted(com_class_of_service_list):
                    is_same_class_of_service = True
                    # print('### HERE : same class of service')
                else:
                    is_same_class_of_service = False
                    # print('### HERE : not same class of service')

                if sorted(prov_fare_basis_code_list) == sorted(com_fare_basis_code_list):
                    is_same_fare_basis_code = True
                    # print('### HERE : same fare basis code')
                else:
                    is_same_fare_basis_code = False
                    # print('### HERE : not same fare basis code')

                process_update_segments_info = False
                if not is_same_journeys or not is_same_departure or not is_same_arrival or not is_same_class_of_service or not is_same_fare_basis_code or not is_same_journey_count:
                    process_update_segments_info = True
                # END

                # resv_segment_str = ';'.join([key for key in resv_segment_dict.keys()])
                # if is_same_journeys:
                #     for journey in commit_data['journeys']:
                #         orig_segment = journey['segments'][0]
                #         dest_segment = journey['segments'][-1]
                #         journey_key = '%s-%s' % (orig_segment['origin'], dest_segment['destination'])
                #         if 'journey_key' in journey and journey['journey_key']:
                #             journey_key = journey['journey_key']
                #
                #         check_journey_level = True
                #         if journey_key not in resv_journey_dict:
                #             _logger.error('Journey not found %s, journey list in data %s' % (journey_key, resv_segment_str))
                #             check_journey_level = False
                #             continue
                #
                #         journey_prov_data = resv_journey_dict[journey_key]
                #         commit_segment_total = len(journey['segments'])
                #         prov_data_segment_total = len(journey_prov_data.segment_ids)
                #
                #         # September 15, 2022 - SAM
                #         # Menambahkan pengecekkan
                #         is_same_departure = True if journey_prov_data.departure_date == orig_segment['departure_date'] else False
                #         is_same_arrival = True if journey_prov_data.arrival_date == dest_segment['arrival_date'] else False
                #         is_same_segment_total = True if commit_segment_total == prov_data_segment_total else False
                #         is_same_class_of_service = False
                #         is_same_fare_basis_code = False
                #         try:
                #             if is_same_segment_total:
                #                 class_of_service_flag_list = []
                #                 fare_basis_code_flag_list = []
                #                 for seg_idx, seg_obj in enumerate(journey_prov_data.segment_ids):
                #                     seg_data = journey['segments'][seg_idx]
                #                     for fare in seg_data.get('fares', []):
                #                         fare_cos = fare.get('class_of_service', '')
                #                         fare_fbc = fare.get('fare_basis_code', '')
                #                         if seg_obj.class_of_service == fare_cos:
                #                             class_of_service_flag_list.append(True)
                #                         else:
                #                             class_of_service_flag_list.append(False)
                #                         if seg_obj.fare_basis_code == fare_fbc:
                #                             fare_basis_code_flag_list.append(True)
                #                         else:
                #                             fare_basis_code_flag_list.append(False)
                #
                #                 if class_of_service_flag_list and all(flag == True for flag in class_of_service_flag_list):
                #                     is_same_class_of_service = True
                #                 if fare_basis_code_flag_list and all(flag == True for flag in fare_basis_code_flag_list):
                #                     is_same_fare_basis_code = True
                #         except:
                #             _logger.error('Error compare class of service in segments')
                #         # END
                #
                #         # if journey_prov_data.departure_date == orig_segment['departure_date'] and journey_prov_data.arrival_date == dest_segment['arrival_date']:
                #         #     if commit_segment_total == prov_data_segment_total:
                #         #         continue
                #
                #         if is_same_departure and is_same_arrival and is_same_segment_total and is_same_class_of_service and is_same_fare_basis_code:
                #             continue
                #
                #         for seg_obj in journey_prov_data.segment_ids:
                #             seg_obj.write({
                #                 'journey_id': None
                #             })
                #             old_segment_list.append(seg_obj.id)
                #
                #         new_segment_obj_list = []
                #         for seg in journey['segments']:
                #             # seg_key = '{origin}-{destination}'.format(**seg)
                #             # if seg_key not in resv_segment_dict:
                #             #     _logger.error('Segment not found %s, segment list in data %s' % (seg_key, resv_segment_str))
                #             #     continue
                #             #
                #             # prov_segment_data = resv_segment_dict[seg_key]
                #             # if prov_segment_data.departure_date == seg['departure_date'] and prov_segment_data.arrival_date == seg['arrival_date']:
                #             #     continue
                #
                #             provider_obj = rsv_prov_obj.provider_id if rsv_prov_obj else None
                #             carrier_obj = self.env['tt.transport.carrier'].sudo().search(
                #                 [('code', '=', seg['carrier_code'])], limit=1)
                #             origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['origin'])],
                #                                                                    limit=1)
                #             destination_obj = self.env['tt.destinations'].sudo().search(
                #                 [('code', '=', seg['destination'])], limit=1)
                #
                #             segment_addons_ids = []
                #             n_seg_values = {
                #                 'segment_code': seg['segment_code'],
                #                 'pnr': commit_data['pnr'],
                #                 'fare_code': '',
                #                 'carrier_code': seg['carrier_code'],
                #                 'carrier_number': seg['carrier_number'],
                #                 'origin_terminal': seg['origin_terminal'],
                #                 'destination_terminal': seg['destination_terminal'],
                #                 'departure_date': seg['departure_date'],
                #                 'arrival_date': seg['arrival_date'],
                #                 'class_of_service': '',
                #                 'cabin_class': '',
                #                 'sequence': seg.get('sequence', 0),
                #             }
                #             if carrier_obj:
                #                 n_seg_values['carrier_id'] = carrier_obj.id
                #             if provider_obj:
                #                 n_seg_values['provider_id'] = provider_obj.id
                #             if origin_obj:
                #                 n_seg_values['origin_id'] = origin_obj.id
                #             if destination_obj:
                #                 n_seg_values['destination_id'] = destination_obj.id
                #
                #             for fare in seg['fares']:
                #                 n_seg_values.update({
                #                     'fare_code': fare['fare_code'],
                #                     'class_of_service': fare['class_of_service'],
                #                     'cabin_class': fare['cabin_class'],
                #                     'fare_basis_code': fare.get('fare_basis_code', ''),
                #                     'tour_code': fare.get('tour_code', ''),
                #                     'fare_class': fare.get('fare_class', ''),
                #                     'fare_name': fare.get('fare_name', ''),
                #                 })
                #                 # for sc in fare['service_charge_summary']:
                #                 #     total_amount += sc['total_price']
                #                 for fare_detail in fare.get('fare_details', []):
                #                     fare_detail_data = copy.deepcopy(fare_detail)
                #                     if not fare_detail_data.get('description'):
                #                         fare_detail_data['description'] = json.dumps('[]')
                #                     else:
                #                         fare_detail_data['description'] = json.dumps(fare_detail_data['description'])
                #                     segment_addons_ids.append((0, 0, fare_detail_data))
                #
                #             n_seg_values.update({
                #                 'segment_addons_ids': segment_addons_ids,
                #             })
                #             n_seg_obj = self.env['tt.segment.reschedule'].sudo().create(n_seg_values)
                #             new_segment_list.append(n_seg_obj.id)
                #             new_segment_obj_list.append(n_seg_obj)
                #
                #             leg_values = {
                #                 'segment_id': n_seg_obj.id,
                #                 'origin_terminal': n_seg_values['origin_terminal'],
                #                 'destination_terminal': n_seg_values['destination_terminal'],
                #                 'departure_date': n_seg_values['departure_date'],
                #                 'arrival_date': n_seg_values['arrival_date'],
                #             }
                #             if n_seg_values.get('carrier_id'):
                #                 leg_values.update({
                #                     'carrier_id': n_seg_values['carrier_id']
                #                 })
                #
                #             if n_seg_values.get('provider_id'):
                #                 leg_values.update({
                #                     'provider_id': n_seg_values['provider_id']
                #                 })
                #
                #             if n_seg_values.get('origin_id'):
                #                 leg_values.update({
                #                     'origin_id': n_seg_values['origin_id']
                #                 })
                #
                #             if n_seg_values.get('destination_id'):
                #                 leg_values.update({
                #                     'destination_id': n_seg_values['destination_id']
                #                 })
                #             self.env['tt.leg.reschedule'].sudo().create(leg_values)
                #
                #             # Membuat data baru untuk reservasi
                #             n_seg_values.update({
                #                 'provider_id': provider_obj.id if provider_obj else None,
                #                 'journey_id': journey_prov_data.id,
                #             })
                #             n_resv_seg_obj = self.env['tt.segment.airline'].sudo().create(n_seg_values)
                #             leg_values.update({
                #                 'segment_id': n_resv_seg_obj.id,
                #                 'provider_id': provider_obj.id if provider_obj else None,
                #             })
                #             self.env['tt.leg.airline'].sudo().create(leg_values)
                #
                #             # Menghilangkan data lama pada tt reservation airline
                #             # prov_segment_data.write({
                #             #     'journey_id': None
                #             # })
                #             # old_segment_list.append(prov_segment_data.id)
                #
                #         # if journey_prov_data.is_vtl_flight != journey.get('is_vtl_flight', False):
                #         #     journey_prov_data.write({
                #         #         'is_vtl_flight': journey['is_vtl_flight']
                #         #     })
                #         origin_id = journey_prov_data.origin_id.id if journey_prov_data.origin_id else None
                #         destination_id = journey_prov_data.destination_id.id if journey_prov_data.destination_id else None
                #         departure_date = journey['departure_date'] if journey.get('departure_date') else ''
                #         arrival_date = journey['arrival_date'] if journey.get('arrival_date') else ''
                #         journey_code = journey['journey_code'] if journey.get('journey_code') else ''
                #         if new_segment_obj_list:
                #             if new_segment_obj_list[0].origin_id:
                #                 origin_id = new_segment_obj_list[0].origin_id.id
                #             if new_segment_obj_list[-1].destination_id:
                #                 destination_id = new_segment_obj_list[-1].destination_id.id
                #         journey_prov_data.write({
                #             'origin_id': origin_id,
                #             'destination_id': destination_id,
                #             'departure_date': departure_date,
                #             'arrival_date': arrival_date,
                #             'journey_code': journey_code,
                #         })
                # else:
                if process_update_segments_info:
                    journey_id_dict_temp = {}
                    # September 23, 2022 - SAM
                    journey_obj_id_list = []
                    journey_obj_list = []

                    # August 6, 2023 - SAM
                    # prov_journey_obj_repo = {}
                    # prov_seg_obj_repo = {}
                    # temp_seg_obj = None
                    for prov_journey_obj in rsv_prov_obj.journey_ids:
                        # origin = prov_journey_obj.origin_id.code if prov_journey_obj.origin_id else ''
                        # destination = prov_journey_obj.destination_id.code if prov_journey_obj.destination_id else ''
                        # jKey = '%s-%s' % (origin, destination)
                        # prov_journey_obj_repo[jKey] = prov_journey_obj
                        for prov_seg_obj in prov_journey_obj.segment_ids:
                            # if not temp_seg_obj:
                            #     temp_seg_obj = prov_seg_obj.copy()
                            #     temp_seg_obj.write({
                            #         'provider_id': None,
                            #         'booking_id': None,
                            #     })
                            prov_seg_obj.write({
                                'journey_id': None,
                            })
                            old_segment_list.append(prov_seg_obj.id)
                            # s_origin = prov_seg_obj.origin_id.code if prov_seg_obj.origin_id else ''
                            # s_destination = prov_seg_obj.destination_id.code if prov_seg_obj.destination_id else ''
                            # sKey = '%s-%s' % (s_origin, s_destination)
                            # prov_seg_obj_repo[sKey] = prov_seg_obj
                        prov_journey_obj.write({
                            'provider_booking_id': None
                        })
                    # END

                    # this_pnr_journey.append((0, 0, {
                    #     'provider_id': provider_id,
                    #     'sequence': journey_sequence,
                    #     'origin_id': this_journey_seg[0][2]['origin_id'],
                    #     'destination_id': this_journey_seg[dest_idx][2]['destination_id'],
                    #     'departure_date': this_journey_seg[0][2]['departure_date'],
                    #     'arrival_date': this_journey_seg[-1][2]['arrival_date'],
                    #     'segment_ids': this_journey_seg,
                    #     'journey_code': journey.get('journey_code', ''),
                    #     'banner_ids': this_journey_banner,
                    #     'is_vtl_flight': journey.get('is_vtl_flight', False),
                    # }))

                    for journey_idx, journey in enumerate(commit_data['journeys']):
                        origin_id = self.env['tt.destinations'].get_id(journey.get('origin', ''), airline_obj.provider_type_id)
                        destination_id = self.env['tt.destinations'].get_id(journey.get('destination', ''), airline_obj.provider_type_id)
                        prov_jrn_obj = self.env['tt.journey.airline'].create({
                            'sequence': journey_idx,
                            'origin_id': origin_id if origin_id else None,
                            'destination_id': destination_id if destination_id else None,
                            'departure_date': journey.get('departure_date', ''),
                            'arrival_date': journey.get('arrival_date', ''),
                            'journey_code': journey.get('journey_code', ''),
                            'provider_booking_id': rsv_prov_obj.id,
                        })
                        new_segment_obj_list = []
                        for seg in journey['segments']:
                            # seg_key = '{origin}-{destination}'.format(**seg)
                            # if seg_key not in resv_segment_dict:
                            #     _logger.error('Segment not found %s, segment list in data %s' % (seg_key, resv_segment_str))
                            #     continue
                            #
                            # prov_segment_data = resv_segment_dict[seg_key]
                            # # if prov_segment_data.departure_date == seg['departure_date'] and prov_segment_data.arrival_date == seg['arrival_date']:
                            # #     continue
                            #
                            # is_same_departure = True if prov_segment_data.departure_date == seg['departure_date'] else False
                            # is_same_arrival = True if prov_segment_data.arrival_date == seg['arrival_date'] else False
                            # is_same_class_of_service = False
                            # is_same_fare_basis_code = False
                            # try:
                            #     class_of_service_flag_list = []
                            #     fare_basis_code_flag_list = []
                            #     for fare in seg.get('fares', []):
                            #         fare_cos = fare.get('class_of_service', '')
                            #         fare_fbc = fare.get('fare_basis_code', '')
                            #         if prov_segment_data.class_of_service == fare_cos:
                            #             class_of_service_flag_list.append(True)
                            #         else:
                            #             class_of_service_flag_list.append(False)
                            #         if prov_segment_data.fare_basis_code == fare_fbc:
                            #             fare_basis_code_flag_list.append(True)
                            #         else:
                            #             fare_basis_code_flag_list.append(False)
                            #
                            #     if class_of_service_flag_list and all(flag == True for flag in class_of_service_flag_list):
                            #         is_same_class_of_service = True
                            #     if fare_basis_code_flag_list and all(flag == True for flag in fare_basis_code_flag_list):
                            #         is_same_fare_basis_code = True
                            # except:
                            #     _logger.error('Error compare class of service in segments')
                            # # END
                            #
                            # # if journey_prov_data.departure_date == orig_segment['departure_date'] and journey_prov_data.arrival_date == dest_segment['arrival_date']:
                            # #     if commit_segment_total == prov_data_segment_total:
                            # #         continue
                            #
                            # if is_same_departure and is_same_arrival and is_same_class_of_service and is_same_fare_basis_code:
                            #     continue
                            #
                            # if seg_key not in journey_id_dict_temp:
                            #     journey_id_dict_temp[seg_key] = {
                            #         'journey_id': prov_segment_data.journey_id.id if prov_segment_data.journey_id else None
                            #     }

                            # if prov_segment_data.id not in old_segment_list:
                            #     old_segment_list.append(prov_segment_data.id)

                            provider_obj = rsv_prov_obj.provider_id if rsv_prov_obj else None
                            carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', seg['carrier_code'])], limit=1)
                            origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['origin']), ('provider_type_id', '=', airline_obj.provider_type_id.id)], limit=1)
                            destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['destination']), ('provider_type_id', '=', airline_obj.provider_type_id.id)], limit=1)
                            segment_addons_ids = []
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
                                'status': seg.get('status', ''),
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
                                    'fare_basis_code': fare.get('fare_basis_code', ''),
                                    'tour_code': fare.get('tour_code', ''),
                                    'fare_class': fare.get('fare_class', ''),
                                    'fare_name': fare.get('fare_name', ''),
                                })
                                # for sc in fare['service_charge_summary']:
                                #     total_amount += sc['total_price']
                                for fare_detail in fare.get('fare_details', []):
                                    fare_detail_data = copy.deepcopy(fare_detail)
                                    if not fare_detail_data.get('description'):
                                        fare_detail_data['description'] = json.dumps('[]')
                                    else:
                                        fare_detail_data['description'] = json.dumps(fare_detail_data['description'])
                                    segment_addons_ids.append((0, 0, fare_detail_data))

                            n_seg_values.update({
                                'segment_addons_ids': segment_addons_ids
                            })
                            n_seg_obj = self.env['tt.segment.reschedule'].sudo().create(n_seg_values)
                            new_segment_list.append(n_seg_obj.id)
                            new_segment_obj_list.append(n_seg_obj)

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
                                'provider_id': provider_obj.id if provider_obj else None,
                                'journey_id': prov_jrn_obj.id,
                            })

                            # if prov_segment_data.journey_id and prov_segment_data.journey_id.id not in journey_obj_id_list:
                            #     journey_obj_id_list.append(prov_segment_data.journey_id.id)
                            #     journey_obj_list.append(prov_segment_data.journey_id)
                            #     prov_segment_data.journey_id.write({
                            #         'journey_code': journey['journey_code'] if journey.get('journey_code') else '',
                            #     })

                            n_resv_seg_obj = self.env['tt.segment.airline'].sudo().create(n_seg_values)
                            leg_values.update({
                                'segment_id': n_resv_seg_obj.id,
                                'provider_id': provider_obj.id if provider_obj else None,
                            })
                            self.env['tt.leg.airline'].sudo().create(leg_values)

                            # Menghilangkan data lama pada tt reservation airline
                            # prov_segment_data.write({
                            #     'journey_id': None
                            # })
                            # if prov_segment_data.id not in old_segment_list:
                            #     old_segment_list.append(prov_segment_data.id)
                        # if prov_segment_data.journey_id.is_vtl_flight != journey.get('is_vtl_flight', False):
                        #     journey_prov_data.write({
                        #         'is_vtl_flight': journey['is_vtl_flight']
                        #     })

                    for journey_obj in journey_obj_list:
                        if journey_obj.segment_ids:
                            journey_obj.write({
                                'origin_id': journey_obj.segment_ids[0].origin_id.id if journey_obj.segment_ids[0].origin_id else None,
                                'destination_id': journey_obj.segment_ids[-1].destination_id.id if journey_obj.segment_ids[-1].destination_id else None,
                                'departure_date': journey_obj.segment_ids[0].departure_date if journey_obj.segment_ids[0].departure_date else '',
                                'arrival_date': journey_obj.segment_ids[-1].arrival_date if journey_obj.segment_ids[-1].arrival_date else '',
                            })
                # END

                # # TODO CEK DATA SSR DAN SEAT
                is_any_ssr_change = False
                old_ssr_notes = []
                new_ssr_notes = []
                for psg in commit_data['passengers']:
                    old_ssr_info_list = []
                    new_ssr_info_list = []
                    psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                    fee_data_list = []
                    for fee in psg['fees']:
                        key = '%s%s%s%s' % (fee['journey_code'], fee['fee_type'], fee['fee_code'], fee['fee_value'])
                        fee_data_list.append(key)
                        new_ssr_info = [
                            'Journey Code : %s' % fee['journey_code'],
                            'Fee Type : %s' % fee['fee_type'],
                            'Fee Code : %s' % fee['fee_code'],
                            'Fee Value : %s' % fee['fee_value'],
                            'Base Price : %s' % fee['base_price'],
                            ''
                        ]
                        new_ssr_info_list.append('\n'.join(new_ssr_info))

                    obj_fee_data_list = []
                    for fee_obj in psg_obj.fee_ids:
                        if not fee_obj.provider_id or fee_obj.provider_id.id != rsv_prov_obj.id:
                            continue

                        fee_journey_code = fee_obj.journey_code and fee_obj.journey_code or ''
                        fee_type = fee_obj.type and fee_obj.type or ''
                        fee_code = fee_obj.code and fee_obj.code or ''
                        fee_value = fee_obj.value and fee_obj.value or ''
                        key = '%s%s%s%s' % (fee_journey_code, fee_type, fee_code, fee_value)
                        obj_fee_data_list.append(key)
                        old_ssr_info = [
                            'Journey Code : %s' % fee_journey_code,
                            'Fee Type : %s' % fee_type,
                            'Fee Code : %s' % fee_code,
                            'Fee Value : %s' % fee_value,
                            ''
                        ]
                        old_ssr_info_list.append('\n'.join(old_ssr_info))

                    # December 7, 2021 - SAM
                    # Fix flow ssr change, deteksi penambahan ssr
                    fee_data_count = len(fee_data_list)
                    obj_fee_data_count = len(obj_fee_data_list)
                    # if set(fee_data_list).difference(set(obj_fee_data_list)) or (not fee_data_list and obj_fee_data_list):
                    if set(fee_data_list).difference(set(obj_fee_data_list)) or (fee_data_count != obj_fee_data_count):
                        is_any_ssr_change = True

                    old_ssr_value = [
                        '# Pax Name : {title} {first_name} {last_name}'.format(**psg),
                        'Fees :',
                        '%s' % '\n'.join(old_ssr_info_list),
                        '',
                    ]
                    old_ssr_notes.append('\n'.join(old_ssr_value))

                    new_ssr_value = [
                        '# Pax Name : {title} {first_name} {last_name}'.format(**psg),
                        'Fees :',
                        '%s' % '\n'.join(new_ssr_info_list),
                        ''
                    ]
                    new_ssr_notes.append('\n'.join(new_ssr_value))

                # # TODO END

                # total_amount = commit_data['total_price'] - rsv_prov_obj.total_price
                total_amount = commit_data['penalty_amount']
                # _logger.info('Vendor Total Price %s, Resv Total Price %s' % (commit_data['total_price'], rsv_prov_obj.total_price))
                if total_amount < 0:
                    total_amount = 0

                # if commit_data['status'] != rsv_prov_obj.state.upper():
                #     pass
                # elif commit_data['status'] == 'ISSUED':
                #     pass
                # elif commit_data['status'] == 'BOOKED':
                #     pass

                admin_fee_obj = None
                is_refund = False

                is_ledger_created = False
                for sc in rsv_prov_obj.cost_service_charge_ids:
                    if sc.is_ledger_created:
                        is_ledger_created = True
                        break

                provider_type_id = airline_obj.provider_type_id and airline_obj.provider_type_id.id or False
                customer_parent_id = airline_obj.customer_parent_id and airline_obj.customer_parent_id.id or False
                if commit_data['status'] == 'BOOKED' and rsv_prov_obj.state == 'booked':
                    ledger_created = rsv_prov_obj.sudo().delete_service_charge()
                    if ledger_created:
                        rsv_prov_obj.action_reverse_ledger()
                        rsv_prov_obj.sudo().delete_service_charge()

                    rsv_prov_obj.sudo().delete_passenger_fees()
                    rsv_prov_obj.sudo().delete_passenger_tickets()
                    rsv_prov_obj.create_ticket_api(commit_data['passengers'], commit_data['pnr'])
                    for journey in commit_data['journeys']:
                        for segment in journey['segments']:
                            for fare in segment['fares']:
                                rsv_prov_obj.create_service_charge(fare['service_charges'])
                                rsv_prov_obj.update_pricing_details(fare)
                elif commit_data['status'] == 'ISSUED' and rsv_prov_obj.state == 'issued':
                    if is_admin_charge:
                        # admin_fee_obj = self.env.ref('tt_accounting.admin_fee_reschedule')
                        admin_fee_obj = self.env['tt.reschedule'].get_reschedule_admin_fee_rule(airline_obj.agent_id.id, customer_parent_id=customer_parent_id, provider_type_id=provider_type_id)
                    rsv_prov_obj.sudo().delete_passenger_fees()
                    for psg in commit_data['passengers']:
                        psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                        psg_obj.create_ssr(psg['fees'], rsv_prov_obj.pnr, rsv_prov_obj.id, is_create_service_charge=False)
                elif commit_data['status'] == 'ISSUED' and rsv_prov_obj.state == 'booked' and is_ledger_created:
                    rsv_prov_obj.write({
                        'state': 'issued'
                    })
                    rsv_prov_obj.sudo().delete_passenger_fees()
                    for psg in commit_data['passengers']:
                        psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                        psg_obj.create_ssr(psg['fees'], rsv_prov_obj.pnr, rsv_prov_obj.id, is_create_service_charge=False)
                    airline_obj.check_provider_state(context)
                elif commit_data['status'] == 'VOID' and rsv_prov_obj.state == 'booked' and commit_data['pnr'] == rsv_prov_obj.pnr:
                    rsv_prov_obj.action_void_api_airline(commit_data, context)
                    continue
                elif commit_data['status'] == 'REFUND' and rsv_prov_obj.state == 'issued' and commit_data['pnr'] == rsv_prov_obj.pnr:
                    # VIN: 2021/03/02: admin fee tdak bisa di hardcode
                    # TODO: refund type tdak boleh hardcode lagi, jika frontend sdah support pilih refund type regular / quick
                    admin_fee_obj = self.env['tt.refund'].get_refund_admin_fee_rule(airline_obj.agent_id.id, customer_parent_id=customer_parent_id, provider_type_id=provider_type_id)
                    refund_type = self.env.ref('tt_accounting.refund_type_regular_refund').id
                    # refund_type = 'regular'

                    refund_line_ids = []

                    # July 21, 2020 - SAM
                    penalty_amount = commit_data['penalty_amount']
                    total_pax = len(commit_data['passengers'])
                    charge_fee = penalty_amount / total_pax
                    # END
                    for psg in commit_data['passengers']:
                        psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                        pax_price = 0
                        additional_charge_fee = 0
                        for cost in psg_obj.cost_service_charge_ids:
                            if cost.description != commit_data['pnr']:
                                continue
                            if cost.charge_type not in ['RAC', 'DISC']:
                                pax_price += cost.amount
                                if cost.charge_type == 'ROC':
                                    additional_charge_fee += cost.amount

                        total_charge_fee = charge_fee + additional_charge_fee
                        line_obj = self.env['tt.refund.line'].create({
                            'name': (psg_obj.title or '') + ' ' + (psg_obj.name or ''),
                            'birth_date': psg_obj.birth_date,
                            'pax_price': pax_price,
                            'charge_fee': total_charge_fee,
                        })
                        refund_line_ids.append(line_obj.id)

                    # July 6, 2021 - SAM
                    # Menyimpan keterangan update cancel booking (v2)
                    # Cancel Reason + Perubahan Detail Service Charges apabila di edit (Amadeus)
                    psg_note_list = []
                    try:
                        if commit_data.get('update_cancel_data') and commit_data['update_cancel_data'].get('passengers'):
                            psg_note_list.append('PNR : %s' % commit_data['pnr'])
                            psg_note_list.append('')
                            for psg in commit_data['update_cancel_data']['passengers']:
                                psg_obj = resv_passenger_number_dict[psg['passenger_number']]
                                psg_note_list.append('Name : %s' % psg_obj.name)
                                reason_code = psg.get('reason_code', '')
                                psg_note_list.append('')
                                if reason_code:
                                    psg_note_list.append('Reason code : %s' % reason_code)
                                for fee in psg.get('fees', []):
                                    for sc_idx, sc in enumerate(fee.get('service_charges', []), 1):
                                        psg_note_list.append('Service Charge sequence %s' % sc_idx)
                                        psg_note_list.append('Charge Type : %s' % sc['charge_type'])
                                        psg_note_list.append('Charge Code : %s' % sc['charge_code'])
                                        psg_note_list.append('Amount : %s' % sc['amount'])
                                        psg_note_list.append('')
                                psg_note_list.append('')
                            psg_note_list.append('')
                    except:
                        _logger.error('Error get passenger notes in Process Update Booking Refund, %s' % traceback.format_exc())

                    if commit_data.get('notes') and commit_data['notes']:
                        psg_note_list.append(commit_data['notes'])

                    notes = '\n'.join(psg_note_list)
                    res_vals = {
                        'agent_id': airline_obj.agent_id.id,
                        'ho_id': airline_obj.ho_id.id,
                        'customer_parent_id': airline_obj.customer_parent_id.id,
                        'booker_id': airline_obj.booker_id.id,
                        'currency_id': airline_obj.currency_id.id,
                        'service_type': airline_obj.provider_type_id.id,
                        'refund_type_id': refund_type,
                        'admin_fee_id': admin_fee_obj.id,
                        'referenced_document': airline_obj.name,
                        'referenced_pnr': airline_obj.pnr,
                        'res_model': airline_obj._name,
                        'res_id': airline_obj.id,
                        'booking_desc': airline_obj.get_aftersales_desc(),
                        'notes': notes,
                        'created_by_api': True,
                    }
                    res_obj = self.env['tt.refund'].create(res_vals)
                    res_obj.confirm_refund_from_button()
                    res_obj.update({
                        'refund_line_ids': [(6, 0, refund_line_ids)],
                    })
                    res_obj.send_refund_from_button()
                    res_obj.validate_refund_from_button()
                    res_obj.finalize_refund_from_button()
                    # June 2, 2022 - SAM
                    if not is_webhook and context.get('co_uid'):
                        co_uid = context['co_uid']
                        res_obj.write({
                            'confirm_uid': co_uid,
                            'sent_uid': co_uid,
                            'validate_uid': co_uid,
                            'finalize_uid': co_uid,
                        })
                    # END
                    continue
                else:
                    try:
                        msg_list = [
                            'Some updates in the reservation are not applied due to different status',
                            '',
                            'Order Number : %s' % airline_obj.name,
                            'Backend Data : %s (%s)' % (commit_data['pnr'], commit_data['status']),
                            'Vendor Data : %s (%s)' % (rsv_prov_obj.pnr, rsv_prov_obj.state.upper()),
                            '',
                            'NOTES :',
                            '- Applied updates for schedule changes',
                            '- Change fees are not applied',
                            '- Change Service charges not applied (for BOOKED reservation)'
                        ]
                        msg = '\n'.join(msg_list)
                        thread_obj = Thread(target=self._do_error_notif, args=('Update Error Notif', msg, airline_obj.ho_id.id))
                        thread_obj.start()
                    except Exception as e:
                        _logger.error('Error do error notif, %s' % str(e))

                if not old_segment_list and not new_segment_list and not is_any_ssr_change:
                    continue

                write_vals = {
                    'balance_due': commit_data['balance_due'],
                    'balance_due_str': commit_data['balance_due_str'],
                }
                if rsv_prov_obj.state != 'issued':
                    write_vals['total_price'] = commit_data['total_price']

                if not is_webhook:
                    write_vals.update({
                        'reschedule_uid': reschedule_uid,
                        'reschedule_date': reschedule_date,
                    })

                rsv_prov_obj.write(write_vals)

                res_vals = {
                    'agent_id': airline_obj.agent_id.id,
                    'ho_id': airline_obj.ho_id.id,
                    'customer_parent_id': airline_obj.customer_parent_id.id,
                    'booker_id': airline_obj.booker_id.id,
                    'currency_id': airline_obj.currency_id.id,
                    'service_type': airline_obj.provider_type_id.id,
                    'referenced_pnr': airline_obj.pnr,
                    'referenced_document': airline_obj.name,
                    'old_segment_ids': [(6, 0, old_segment_list)],
                    'new_segment_ids': [(6, 0, new_segment_list)],
                    # 'reschedule_line_ids': [(6, 0, reschedule_line_list)],
                    'passenger_ids': [(6, 0, passenger_list)],
                    'res_model': airline_obj._name,
                    'res_id': airline_obj.id,
                    'notes': commit_data.get('notes') and commit_data['notes'] or '',
                    'old_fee_notes': '\n'.join(old_ssr_notes) if old_ssr_notes else '',
                    'new_fee_notes': '\n'.join(new_ssr_notes) if new_ssr_notes else '',
                    'payment_acquirer_id': payment_acquirer_obj.id,
                    'created_by_api': True,
                }

                is_reschedule_created = False
                if 'reschedule_id' in commit_data:
                    is_reschedule_created = True
                    rsch_obj = self.env['tt.reschedule'].browse(commit_data['reschedule_id'])
                    res_vals.pop('service_type')
                    rsch_obj.write(res_vals)
                    for rsch_pax in rsch_obj.passenger_ids:
                        # fill RS number to pax's reschedule CSCs with empty description
                        for rsch_p_csc in rsch_pax.channel_service_charge_ids.filtered(lambda x: 'rs' in x.charge_code.split('.')):
                            if not rsch_p_csc.description:
                                rsch_p_csc.update({
                                    'description': rsch_obj.name
                                })

                    # June 2, 2022 - SAM
                    co_uid = context.get('co_uid') if not is_webhook else ''
                    if rsv_prov_obj.state == 'issued':
                        # rsch_obj.finalize_reschedule_from_button()
                        # rsch_obj.action_done(bypass_po=True)
                        rsch_obj.finalize_reschedule_from_api(co_uid=co_uid)
                        rsch_obj.action_done_from_api(bypass_po=True, co_uid=co_uid)
                    else:
                        # rsch_obj.cancel_reschedule_from_button()
                        rsch_obj.cancel_reschedule_from_api(co_uid=co_uid)
                    # END
                else:
                    rsch_obj = self.env['tt.reschedule'].create(res_vals)
                    for rsch_pax in rsch_obj.passenger_ids:
                        # fill RS number to pax's reschedule CSCs with empty description
                        for rsch_p_csc in rsch_pax.channel_service_charge_ids.filtered(lambda x: 'rs' in x.charge_code.split('.')):
                            if not rsch_p_csc.description:
                                rsch_p_csc.update({
                                    'description': rsch_obj.name
                                })

                    rsch_line_values = {
                        'reschedule_type': 'reschedule' if new_segment_list else 'addons',
                        'reschedule_amount': total_amount,
                        'reschedule_amount_ho': total_amount,
                        'real_reschedule_amount': total_amount,
                        'reschedule_id': rsch_obj.id,
                        'provider_id': self.env['tt.provider.airline'].browse(commit_data['provider_id']).provider_id.id
                    }
                    if admin_fee_obj:
                        rsch_line_values.update({
                            'admin_fee_id': admin_fee_obj.id
                        })
                    rsch_line_obj = self.env['tt.reschedule.line'].sudo().create(rsch_line_values)
                    # END

                    # VIN: 22/10/2020 Check klo book tetep di catet cman ledger agent tidak terpotong
                    # June 2, 2022 - SAM
                    if rsv_prov_obj.state == 'issued':
                        # # July 13, 2020 - SAM
                        # # Sementara diasumsikan untuk seluruh proses berhasil
                        # rsch_obj.confirm_reschedule_from_api(context.get('co_uid'))
                        # rsch_obj.send_reschedule_from_button()
                        # rsch_obj.validate_reschedule_from_button()
                        # rsch_obj.finalize_reschedule_from_button()
                        # # Klo dari API dia bypass PO
                        # rsch_obj.action_done(bypass_po=True)
                        # # END
                        co_uid = context.get('co_uid') if not is_webhook else False
                        rsch_obj.confirm_reschedule_from_api(co_uid=co_uid)
                        rsch_obj.send_reschedule_from_api(co_uid=co_uid)
                        agent_payment_method = 'balance'
                        if vals.get('agent_payment_method'):
                            agent_payment_method = vals['agent_payment_method']
                        rsch_obj.validate_reschedule_from_api(co_uid=co_uid, agent_payment_method=agent_payment_method)
                        rsch_obj.finalize_reschedule_from_api(co_uid=co_uid)
                        rsch_obj.action_done_from_api(bypass_po=True, co_uid=co_uid)
                    else:
                        # rsch_obj.cancel_reschedule_from_button()
                        co_uid = context.get('co_uid') if not is_webhook else False
                        rsch_obj.cancel_reschedule_from_api(co_uid=co_uid)

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

                origin_id = dest_obj.get_id(origin_code, airline_obj.provider_type_id)
                destination_id = dest_obj.get_id(destination_code, airline_obj.provider_type_id)

                new_vals = {
                    'split_from_resv_id': airline_obj.id,
                    'split_uid': self.env.user.id,
                    'split_date': fields.Datetime.now(),
                    # 'pnr': ','.join(pnr_list),
                    'agent_id': airline_obj.agent_id and airline_obj.agent_id.id or False,
                    'ho_id': airline_obj.ho_id and airline_obj.ho_id.id or False,
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
                    'contact_name': airline_obj.contact_name,
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
                ## split hapus voucher
                new_resv_obj.delete_voucher()
                airline_obj.delete_voucher()
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

                ## 27 Jul 2023 add CSC
                data_request_upsell = {
                    "order_number": new_resv_obj.name,
                    "passengers": [],
                    "provider_type": 'airline'
                }
                for psg_obj in new_resv_obj.passenger_ids:
                    for psg_dict in commit_data['passengers']:
                        if psg_obj.id == psg_dict['passenger_id'] and psg_dict.get('upsell'):
                            pax_upsell = {
                                "pricing": []
                            }
                            for data_upsell_dict in psg_dict['upsell']:
                                pax_upsell['pricing'].append({
                                    "currency_code": data_upsell_dict['currency'],
                                    "amount": data_upsell_dict['amount']
                                })
                            psg_obj.create_channel_pricing(pax_upsell['pricing'])
                # if pax_upsell:
                #     data_request_upsell['passengers'] = pax_upsell
                #     new_resv_obj.channel_pricing_api(data_request_upsell, context) ## ga bisa di pakai karena fungsi langsung calculate nanti harga di provider kosong
                #####


                self.env['tt.reservation.airline'].update_pnr_provider_airline_api(new_payload, context)
                new_resv_passenger_number_dict = {}
                for psg in new_resv_obj.passenger_ids:
                    key_number = psg.sequence
                    new_resv_passenger_number_dict[key_number] = psg
                for prov in new_resv_obj.provider_booking_ids:
                    if prov.state in ['issued', 'refund']:
                        prov.action_create_ledger(new_resv_obj.issued_uid.id)

                    if prov.state == 'refund':
                        # VIN: 2021/03/02: admin fee tdak bisa di hardcode
                        # TODO: refund type tdak boleh hardcode lagi, jika frontend sdah support pilih refund type regular / quick
                        provider_type_id = new_resv_obj.provider_type_id and new_resv_obj.provider_type_id.id or False
                        customer_parent_id = new_resv_obj.customer_parent_id and new_resv_obj.customer_parent_id.id or False
                        admin_fee_obj = self.env['tt.refund'].get_refund_admin_fee_rule(new_resv_obj.agent_id.id, customer_parent_id=customer_parent_id, provider_type_id=provider_type_id)
                        refund_type = self.env.ref('tt_accounting.refund_type_regular_refund').id
                        # refund_type = 'regular'

                        refund_line_ids = []

                        # July 21, 2020 - SAM
                        penalty_amount = commit_data['penalty_amount']
                        total_pax = len(commit_data['passengers'])
                        charge_fee = penalty_amount / total_pax
                        # END
                        for psg in commit_data['passengers']:
                            psg_obj = new_resv_passenger_number_dict[psg['passenger_number']]
                            pax_price = 0
                            additional_charge_fee = 0
                            for cost in psg_obj.cost_service_charge_ids:
                                if cost.description != commit_data['pnr']:
                                    continue
                                if cost.charge_type not in ['RAC', 'DISC']:
                                    pax_price += cost.amount
                                    if cost.charge_type == 'ROC':
                                        additional_charge_fee += cost.amount

                            total_charge_fee = charge_fee + additional_charge_fee
                            line_obj = self.env['tt.refund.line'].create({
                                'name': (psg_obj.title or '') + ' ' + (psg_obj.name or ''),
                                'birth_date': psg_obj.birth_date,
                                'pax_price': pax_price,
                                'charge_fee': total_charge_fee,
                            })
                            refund_line_ids.append(line_obj.id)

                        res_vals = {
                            'agent_id': new_resv_obj.agent_id.id,
                            'ho_id': new_resv_obj.ho_id.id,
                            'customer_parent_id': new_resv_obj.customer_parent_id.id,
                            'booker_id': new_resv_obj.booker_id.id,
                            'currency_id': new_resv_obj.currency_id.id,
                            'service_type': new_resv_obj.provider_type_id.id,
                            'refund_type_id': refund_type,
                            'admin_fee_id': admin_fee_obj.id,
                            'referenced_document': new_resv_obj.name,
                            'referenced_pnr': new_resv_obj.pnr,
                            'res_model': new_resv_obj._name,
                            'res_id': new_resv_obj.id,
                            'booking_desc': new_resv_obj.get_aftersales_desc(),
                            'notes': commit_data.get('notes') and commit_data['notes'] or '',
                            'created_by_api': True,
                        }
                        res_obj = self.env['tt.refund'].create(res_vals)
                        res_obj.confirm_refund_from_button()
                        res_obj.update({
                            'refund_line_ids': [(6, 0, refund_line_ids)],
                        })
                        res_obj.send_refund_from_button()
                        res_obj.validate_refund_from_button()
                        res_obj.finalize_refund_from_button()
                        # June 2, 2022 - SAM
                        co_uid = context.get('co_uid')
                        if not is_webhook and co_uid:
                            res_obj.write({
                                'confirm_uid': co_uid,
                                'sent_uid': co_uid,
                                'validate_uid': co_uid,
                                'finalize_uid': co_uid,
                            })
                        # END

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
                    psg_obj.sudo().unlink()

            for prov_obj in airline_obj.provider_booking_ids:
                for journey_obj in prov_obj.journey_ids:
                    journey_obj.compute_detail_info()
                prov_obj.write({
                    'departure_date': prov_obj.journey_ids[0].departure_date,
                    'arrival_date': prov_obj.journey_ids[-1].arrival_date,
                })

            # October 25, 2023 - SAM
            # Compute destination baru
            is_valid = True
            new_origin_id = None
            new_destination_id = None
            last_destination_id = None
            route_list = []
            if airline_obj.journey_ids and airline_obj.journey_ids[0].origin_id:
                route_list = [airline_obj.journey_ids[0].origin_id.code]
                new_origin_id = airline_obj.journey_ids[0].origin_id.id
            for journey_obj in airline_obj.journey_ids:
                if not journey_obj.origin_id or not journey_obj.destination_id:
                    is_valid = False
                    break

                origin_code = journey_obj.origin_id.code
                if origin_code not in route_list:
                    new_destination_id = last_destination_id
                    break
                destination_code = journey_obj.destination_id.code
                if destination_code in route_list:
                    new_destination_id = last_destination_id
                    break
                route_list.append(destination_code)
                last_destination_id = journey_obj.destination_id.id

            if not is_valid:
                new_origin_id = None
                new_destination_id = None
                if airline_obj.journey_ids:
                    if airline_obj.journey_ids[0].origin_id:
                        new_origin_id = airline_obj.journey_ids[0].origin_id.id
                    if airline_obj.journey_ids[0].destination_id:
                        new_destination_id = airline_obj.journey_ids[0].destination_id.id
            else:
                if not new_destination_id:
                    new_destination_id = last_destination_id

            airline_obj.write({
                'adult': adult,
                'child': child,
                'infant': infant,
                'departure_date': airline_obj.journey_ids[0].departure_date[:10] if airline_obj.journey_ids else '',
                'origin_id': new_origin_id,
                'destination_id': new_destination_id,
            })
            airline_obj.calculate_service_charge()

            # January 20, 2022 - SAM
            # Buat fungsi manual untuk write data pada reservasi
            # Karena kalau menggunakan fungsi dibawah akan trigger fungsi button
            # Sehingga untuk status issued akan berubah tanggal issuednya
            # airline_obj.check_provider_state(context)
            airline_obj.set_provider_detail_info()
            if not is_webhook:
                rsv_vals = {
                    'reschedule_uid': reschedule_uid,
                    'reschedule_date': reschedule_date,
                }
                airline_obj.write(rsv_vals)
            # END
            airline_obj.create_svc_upsell()

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

    def _do_error_notif(self, title, message, ho_id):
        data = {
            'code': 9903,
            'title': title,
            'message': message,
        }
        context = {
            "co_ho_id": ho_id
        }
        ## tambah context
        ## kurang test
        GatewayConnector().telegram_notif_api(data, context)
        return True

    # January 4, 2021 - SAM
    # Fungi update booking v2 after sales
    def create_update_booking_payment_api(self, vals, context):
        try:
            if 'use_system_user' in vals and vals['use_system_user']:
                context.update({
                    'co_uid': self.env.uid
                })
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
            resv_segment_dict = {}
            for journey in airline_obj.journey_ids:
                key = '%s%s' % (journey.origin_id.code if journey.origin_id else '', journey.destination_id.code if journey.destination_id else '')
                resv_journey_dict[key] = journey
                for seg in journey.segment_ids:
                    origin = seg.origin_id.code if seg.origin_id else '-'
                    destination = seg.destination_id.code if seg.destination_id else '-'
                    seg_key = '%s%s' % (origin, destination)
                    resv_segment_dict[seg_key] = seg

            resv_passenger_number_dict = {}
            for psg in airline_obj.passenger_ids:
                key_number = psg.sequence
                resv_passenger_number_dict[key_number] = psg

            resv_provider_dict = {}
            for prov in airline_obj.provider_booking_ids:
                # key = prov.pnr
                key = prov.id
                resv_provider_dict[key] = prov

            is_admin_charge = True
            if 'is_admin_charge' in vals:
                is_admin_charge = vals['is_admin_charge']

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
            # if not payment_acquirer_obj: #BOOKED TIDAK KIRIM seq_id
            #     return ERR.get_error(1017)
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

                total_amount = commit_data['total_price']
                if total_amount < 0:
                    total_amount = 0

                # August 30, 2022 - SAM
                # TODO sementara reschedule type diasumsikan reschedule kalau ada admin charge
                provider_type_id = airline_obj.provider_type_id and airline_obj.provider_type_id.id or False
                customer_parent_id = airline_obj.customer_parent_id and airline_obj.customer_parent_id.id or False
                admin_fee_obj = None
                reschedule_type = 'addons'
                if is_admin_charge:
                    reschedule_type = 'reschedule'
                    admin_fee_obj = self.env['tt.reschedule'].get_reschedule_admin_fee_rule(airline_obj.agent_id.id, customer_parent_id=customer_parent_id, provider_type_id=provider_type_id)

                res_vals = {
                    'agent_id': airline_obj.agent_id.id,
                    'ho_id': airline_obj.ho_id.id,
                    'customer_parent_id': airline_obj.customer_parent_id.id,
                    'booker_id': airline_obj.booker_id.id,
                    'currency_id': airline_obj.currency_id.id,
                    'service_type': str(airline_obj.provider_type_id.id),
                    'referenced_pnr': airline_obj.pnr,
                    'referenced_document': airline_obj.name,
                    'old_segment_ids': [],
                    'new_segment_ids': [],
                    'passenger_ids': [],
                    'res_model': airline_obj._name,
                    'res_id': airline_obj.id,
                    'notes': vals.get('notes') and vals['notes'] or '',
                    'old_fee_notes': '',
                    'new_fee_notes': '',
                    'payment_acquirer_id': payment_acquirer_obj.id,
                    'created_by_api': True,
                }
                rsch_obj = self.env['tt.reschedule'].create(res_vals)

                rsch_line_values = {
                    'reschedule_type': reschedule_type,
                    'reschedule_amount': total_amount,
                    'reschedule_amount_ho': total_amount,
                    'real_reschedule_amount': total_amount,
                    'reschedule_id': rsch_obj.id,
                    'provider_id': self.env['tt.provider.airline'].browse(commit_data['provider_id']).provider_id.id
                }
                if admin_fee_obj:
                    rsch_line_values.update({
                        'admin_fee_id': admin_fee_obj.id
                    })
                rsch_line_obj = self.env['tt.reschedule.line'].sudo().create(rsch_line_values)
                # END

                if rsv_prov_obj.state == 'issued':
                    rsch_obj.confirm_reschedule_from_api(context.get('co_uid'))
                    rsch_obj.send_reschedule_from_button()
                    agent_payment_method = 'balance'
                    if vals.get('agent_payment_method'):
                        agent_payment_method = vals['agent_payment_method']
                    rsch_obj.payment_method_to_ho = agent_payment_method
                    rsch_obj.validate_reschedule_from_button(agent_payment_method)

                commit_data.update({
                    'reschedule_id': rsch_obj.id
                })

            return ERR.get_no_error(vals)
        except RequestException as e:
            _logger.error('Error Create Update Booking Payment API, %s' % traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Create Update Booking Payment API, %s' % traceback.format_exc())
            return ERR.get_error(1030)

    # END