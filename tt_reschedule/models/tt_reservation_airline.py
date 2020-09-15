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
            for rec in vals['update_booking_provider']:
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

            # Menambahkan untuk field harga
            rsch_line_values = {
                'reschedule_type': reschedule_type,
                'reschedule_amount': total_amount,
                'reschedule_amount_ho': total_amount,
                'real_reschedule_amount': total_amount,
                'admin_fee_id': admin_fee_obj.id,
            }
            rsch_line_obj = self.env['tt.reschedule.line'].sudo().create(rsch_line_values)
            reschedule_line_list = [rsch_line_obj.id]
            reschedule_obj.write({
                'reschedule_line_ids': [(6, 0, reschedule_line_list)],
                'notes': '\n'.join(note_list),
            })
            # END

            # July 13, 2020 - SAM
            # Sementara diasumsikan untuk seluruh proses berhasil
            reschedule_obj.confirm_reschedule_from_button()
            reschedule_obj.send_reschedule_from_button()
            reschedule_obj.validate_reschedule_from_button()
            reschedule_obj.finalize_reschedule_from_button()
            # reschedule_obj.action_done()
            # END

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
