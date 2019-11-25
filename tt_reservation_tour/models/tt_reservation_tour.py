from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import logging
import traceback
import copy
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response

# from Ap
_logger = logging.getLogger(__name__)

PAYMENT_METHOD = [
    ('full', 'Full Payment'),
    ('installment', 'Installment')
]


class ReservationTourRoom(models.Model):
    _name = 'tt.reservation.tour.room'
    _description = 'Rodex Model'

    booking_id = fields.Many2one('tt.reservation.tour', 'Reservation Tour')
    room_id = fields.Many2one('tt.master.tour.rooms', 'Room')
    notes = fields.Text('Notes')


class ReservationTour(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.tour'
    _order = 'id DESC'
    _description = 'Rodex Model'

    tour_id = fields.Many2one('tt.master.tour', 'Tour ID')
    # tour_id = fields.Char('Tour ID')

    room_ids = fields.One2many('tt.reservation.tour.room', 'booking_id', 'Rooms')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_tour_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})
    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger',
                                 domain=[('res_model', '=', 'tt.reservation.tour')])
    provider_booking_ids = fields.One2many('tt.provider.tour', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.tour', 'booking_id', string='Passengers')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_tour.tt_provider_type_tour'))
    payment_method = fields.Selection(PAYMENT_METHOD, 'Payment Method')
    installment_invoice_ids = fields.One2many('tt.installment.invoice', 'booking_id', 'Installments')

    def action_issued_tour(self, api_context=None):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        if not api_context.get('co_uid'):
            api_context.update({
                'co_uid': self.env.user.id
            })

        if self.state != 'issued':
            self.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': api_context['co_uid'] or self.env.user.id,
            })
            for rec in self.provider_booking_ids:
                rec.action_create_ledger(self.env.user.id)

    def call_create_invoice(self, acquirer_id, payment_method):
        _logger.info('Creating Invoice for ' + self.name)

    def update_pnr_data(self, book_id, pnr):
        provider_objs = self.env['tt.provider.tour'].search([('booking_id', '=', book_id)])
        for rec in provider_objs:
            rec.sudo().write({
                'pnr': pnr
            })
            cost_service_charges = self.env['tt.service.charge'].search([('provider_tour_booking_id', '=', rec.id)])
            for rec2 in cost_service_charges:
                rec2.sudo().write({
                    'description': pnr
                })

    def action_reissued(self):
        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
        if (self.tour_id.seat - pax_amount) >= 0:
            self.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': self.env.user.id
            })
            # self.message_post(body='Order REISSUED')
        else:
            raise UserError(
                _('Cannot reissued because there is not enough seat quota.'))

    def action_refund(self):
        self.write({
            'state': 'refund',
            'refund_date': datetime.now(),
            'refund_uid': self.env.user.id
        })
        # self.message_post(body='Order REFUNDED')

        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
        self.tour_id.seat += pax_amount
        if self.tour_id.seat > self.tour_id.quota:
            self.tour_id.seat = self.tour_id.quota
        self.tour_id.state = 'open'

        print('state : ' + self.state)

    def action_cancel(self):
        self.write({
            'state': 'cancel',
            'cancel_date': datetime.now(),
            'cancel_uid': self.env.user.id
        })
        # self.message_post(body='Order CANCELED')

        if self.state != 'refund':
            pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
            self.tour_id.seat += pax_amount
            if self.tour_id.seat > self.tour_id.quota:
                self.tour_id.seat = self.tour_id.quota
            self.tour_id.state = 'open'

        for rec in self.tour_id.passengers_ids:
            if rec.tour_id.id == self.id:
                rec.sudo().write({
                    'tour_id': False
                })
    # *END STATE*

    def action_booked_tour(self, api_context=None):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        if not api_context.get('co_uid'):
            api_context.update({
                'co_uid': self.env.user.id
            })

        if self.state != 'booked':
            self.write({
                'state': 'booked',
                'booked_date': datetime.now(),
                'booked_uid': api_context['co_uid'] or self.env.user.id,
                'hold_date': datetime.now() + relativedelta(days=1),
            })

        # Kurangi seat sejumlah pax_amount, lalu cek sisa kuota tour
        pax_amount = sum(1 for temp in self.passenger_ids if temp.pax_type != 'INF')  # jumlah orang yang di book
        self.tour_id.seat -= pax_amount  # seat tersisa dikurangi jumlah orang yang di book
        if self.tour_id.seat <= int(0.2 * self.tour_id.quota):
            self.tour_id.state = 'definite'  # pasti berangkat jika kuota >=80%
        if self.tour_id.seat == 0:
            self.tour_id.state = 'sold'  # kuota habis

    def action_cancel_by_manager(self):
        self.action_refund()
        self.action_cancel()
        # refund

    #############################################################################################################
    #############################################################################################################

    def get_id(self, booking_number):
        row = self.env['tt.reservation.tour'].search([('name', '=', booking_number)])
        if not row:
            return ''
        return row.id

    ############################################################################################################
    ############################################################################################################

    # to generate sale service charge
    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        for provider in self.provider_booking_ids:
            sc_value = {}
            for p_sc in provider.cost_service_charge_ids:
                p_charge_code = p_sc.charge_code
                p_charge_type = p_sc.charge_type
                p_pax_type = p_sc.pax_type
                if not sc_value.get(p_pax_type):
                    sc_value[p_pax_type] = {}
                if p_charge_type != 'RAC':
                    if not sc_value[p_pax_type].get(p_charge_type):
                        sc_value[p_pax_type][p_charge_type] = {}
                        sc_value[p_pax_type][p_charge_type].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0
                        })
                    c_type = p_charge_type
                    c_code = p_charge_type.lower()
                elif p_charge_type == 'RAC':
                    if not sc_value[p_pax_type].get(p_charge_code):
                        sc_value[p_pax_type][p_charge_code] = {}
                        sc_value[p_pax_type][p_charge_code].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0
                        })
                    c_type = p_charge_code
                    c_code = p_charge_code
                sc_value[p_pax_type][c_type].update({
                    'charge_type': p_charge_type,
                    'charge_code': c_code,
                    'pax_count': p_sc.pax_count,
                    'currency_id': p_sc.currency_id.id,
                    'foreign_currency_id': p_sc.foreign_currency_id.id,
                    'amount': sc_value[p_pax_type][c_type]['amount'] + p_sc.amount,
                    'total': sc_value[p_pax_type][c_type]['total'] + p_sc.total,
                    'foreign_amount': sc_value[p_pax_type][c_type]['foreign_amount'] + p_sc.foreign_amount,
                })

            values = []
            for p_type, p_val in sc_value.items():
                for c_type, c_val in p_val.items():
                    curr_dict = {}
                    curr_dict['pax_type'] = p_type
                    curr_dict['booking_tour_id'] = self.id
                    curr_dict['description'] = provider.pnr
                    curr_dict.update(c_val)
                    values.append((0, 0, curr_dict))

            self.write({
                'sale_service_charge_ids': values
            })

    def commit_booking_api(self, data, context, **kwargs):
        try:
            booker_data = data.get('booker_data') and data['booker_data'] or False
            contacts_data = data.get('contacts_data') and data['contacts_data'] or False
            passengers = data.get('passengers_data') and data['passengers_data'] or False
            force_issued = data.get('force_issued') and int(data['force_issued']) or False
            pricelist_id = data.get('tour_id') and int(data['tour_id']) or 0
            room_list = data.get('room_list') and data['room_list'] or []
            tour_data = self.env['tt.master.tour'].sudo().search([('id', '=', pricelist_id)], limit=1)
            pricing = data.get('pricing') and data['pricing'] or []
            if tour_data:
                tour_data = tour_data[0]
            provider_id = tour_data.provider_id
            total_all_pax = int(data.get('adult')) + int(data.get('child')) + int(data.get('infant'))
            if tour_data.seat - total_all_pax < 0:
                raise RequestException(1004, additional_message='Not enough seats. Seats available: %s/%s' % (tour_data.seat, tour_data.quota,))

            booker_obj = self.create_booker_api(booker_data, context)
            contact_data = contacts_data[0]
            contact_objs = []
            for con in contacts_data:
                contact_objs.append(self.create_contact_api(con, booker_obj, context))

            contact_obj = contact_objs[0]

            list_passenger_value = self.create_passenger_value_api_test(passengers)
            pax_ids = self.create_customer_api(passengers, context, booker_obj.seq_id, contact_obj.seq_id)

            for idx, temp_pax in enumerate(passengers):
                list_passenger_value[idx][2].update({
                    'customer_id': pax_ids[idx].id,
                    'title': temp_pax['title'],
                    'pax_type': temp_pax['pax_type'],
                    'tour_room_id': temp_pax.get('tour_room_id', 0),
                    'master_tour_id': tour_data and tour_data.id or False,
                })

            try:
                agent_obj = self.env['tt.customer'].browse(int(booker_obj.id)).agent_id
                if not agent_obj:
                    agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            except Exception:
                agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id

            booking_obj = self.env['tt.reservation.tour'].sudo().create({
                'contact_id': contact_obj.id,
                'booker_id': booker_obj.id,
                'passenger_ids': list_passenger_value,
                'contact_title': contact_data['title'],
                'contact_name': contact_data['first_name'] + ' ' + contact_data['last_name'],
                'contact_email': contact_data.get('email') and contact_data['email'] or '',
                'contact_phone': contact_data.get('mobile') and str(contact_data['calling_code']) + str(
                    contact_data['mobile']),
                'agent_id': context['co_agent_id'],
                'user_id': context['co_uid'],
                'tour_id': pricelist_id,
                'adult': data.get('adult') and int(data['adult']) or 0,
                'child': data.get('child') and int(data['child']) or 0,
                'infant': data.get('infant') and int(data['infant']) or 0,
                'departure_date': tour_data.departure_date,
                'return_date': tour_data.return_date,
                'provider_name': provider_id.name,
                'transport_type': 'tour',
            })

            if booking_obj:
                for room in room_list:
                    room.update({
                        'booking_id': booking_obj.id
                    })
                    self.env['tt.reservation.tour.room'].sudo().create(room)

                booking_obj.action_booked_tour(context)

                provider_tour_vals = {
                    'booking_id': booking_obj.id,
                    'tour_id': pricelist_id,
                    'provider_id': provider_id.id,
                    'departure_date': tour_data['departure_date'],
                    'return_date': tour_data['return_date'],
                    # 'balance_due': req['amount'],
                }

                provider_tour_obj = self.env['tt.provider.tour'].sudo().create(provider_tour_vals)
                for psg in booking_obj.passenger_ids:
                    vals = {
                        'provider_id': provider_tour_obj.id,
                        'passenger_id': psg.id,
                        'pax_type': psg.pax_type,
                        'tour_room_id': psg.tour_room_id.id
                    }
                    self.env['tt.ticket.tour'].sudo().create(vals)
                provider_tour_obj.delete_service_charge()
                provider_tour_obj.create_service_charge(pricing)

                response = {
                    'order_id': booking_obj.id,
                    'order_number': booking_obj.name,
                }
            else:
                response = {
                    'order_number': 0
                }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                booking_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                booking_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def issued_booking_api(self, data, context, **kwargs):
        try:
            book_objs = self.env['tt.reservation.tour'].sudo().search([('name', '=', data['order_number'])], limit=1)
            book_obj = book_objs[0]

            try:
                agent_obj = self.env['tt.customer'].browse(int(self.booker_id.id)).agent_id
                if not agent_obj:
                    agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            except Exception:
                agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id

            payment_method = data.get('payment_method') and data['payment_method'] or 'full'

            if payment_method == 'full':
                is_enough = self.env['tt.agent'].check_balance_limit_api(agent_obj.id, book_obj.agent_nta)
            else:
                total_dp = 0
                for rec in book_obj.tour_id.payment_rules_ids:
                    if rec.is_dp:
                        if rec.payment_type == 'amount':
                            total_dp += rec.payment_amount
                        else:
                            total_dp += (rec.payment_percentage / 100) * book_obj.agent_nta
                is_enough = self.env['tt.agent'].check_balance_limit_api(agent_obj.id, total_dp)
            if is_enough['error_code'] != 0:
                _logger.error('Balance not enough')
                raise RequestException(1007)

            if data.get('member'):
                customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', data['seq_id'])])
            else:
                customer_parent_id = book_obj.agent_id.customer_parent_walkin_id.id

            vals = {
                'customer_parent_id': customer_parent_id,
                'payment_method': payment_method
            }

            book_obj.sudo().write(vals)
            book_obj.action_issued_tour(context)
            if data.get('seq_id'):
                acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', data['seq_id'])])
                if not acquirer_id:
                    raise RequestException(1017)
            else:
                raise RequestException(1017)

            book_obj.call_create_invoice(acquirer_id, payment_method)

            response = {
                'order_id': book_obj.id,
                'order_number': book_obj.name,
                'state': book_obj.state,
                'pnr': book_obj.pnr,
                'provider': book_obj.tour_id.provider_id.code,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def get_booking_api(self, data, context, **kwargs):
        try:
            search_booking_num = data['order_number']
            book_obj = self.env['tt.reservation.tour'].sudo().search([('name', '=', search_booking_num)], limit=1)
            if book_obj:
                book_obj = book_obj[0]

            master = self.env['tt.master.tour'].browse(book_obj.tour_id.id)
            image_urls = []
            for img in master.image_ids:
                image_urls.append(str(img.url))

            tour_package = {
                'id': master.id,
                'name': master.name,
                'duration':master.duration,
                'departure_date': master.departure_date,
                'return_date': master.return_date,
                'visa': master.visa,
                'flight': master.flight,
                'image_urls': image_urls,
            }

            passengers = []
            for rec in book_obj.sudo().passenger_ids:
                passengers.append(rec.to_dict())
            contact = self.env['tt.customer'].browse(book_obj.contact_id.id)

            rooms = []
            room_idx = 1
            for room_data in book_obj.room_ids:
                rooms.append({
                    'room_index': room_idx,
                    'room_id': room_data.room_id.id,
                    'room_name': room_data.room_id.name,
                    'room_bed_type': room_data.room_id.bed_type,
                    'room_hotel': room_data.room_id.hotel and room_data.room_id.hotel or '-',
                    'room_desc': room_data.room_id.description and room_data.room_id.description or '-',
                    'room_notes': room_data.notes and room_data.notes or '-',
                })
                room_idx += 1

            for psg in passengers:
                for temp_room in rooms:
                    if int(psg['tour_room_id']) == int(temp_room['room_id']):
                        psg.update({
                            'tour_room_string': temp_room['room_name'] + ' (' + temp_room['room_hotel'] + ')'
                        })
                        break

            for psg in passengers:
                psg.pop('tour_room_id')

            for temp_room in rooms:
                temp_room.pop('room_id')

            response = {
                'booker_seq_id': book_obj.booker_id.seq_id,
                'contacts': {
                    'email': book_obj.contact_email,
                    'name': book_obj.contact_name,
                    'phone': book_obj.contact_phone,
                    'gender': contact.gender and contact.gender or '',
                    'marital_status': contact.marital_status and contact.marital_status or False,
                },
                'passengers': passengers,
                'pnr': book_obj.pnr,
                'state': book_obj.state,
                'adult': book_obj.adult,
                'child': book_obj.child,
                'infant': book_obj.infant,
                'departure_date': book_obj.departure_date,
                'return_date': book_obj.return_date,
                'order_number': book_obj.name,
                'hold_date': book_obj.hold_date,
                'tour_details': tour_package,
                'rooms': rooms,
                'grand_total': book_obj.total,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def update_booking_api(self, data, context, **kwargs):
        try:
            book_objs = self.env['tt.reservation.tour'].sudo().search([('name', '=', data['order_number'])])
            book_obj = book_objs[0]
            write_vals = {
                'sid_booked': context.get('sid') and context['sid'] or '',
            }
            book_info = data.get('book_info') and data['book_info'] or {}
            if book_info:
                write_vals.update({
                    'pnr': book_info.get('pnr') and book_info['pnr'] or ''
                })

            book_obj.sudo().write(write_vals)
            book_obj.update_pnr_data(book_obj.id, book_info['pnr'])
            book_obj.calculate_service_charge()
            self.env.cr.commit()

            response = {
                'order_number': book_obj.name,
                'state': book_obj.state,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1005)


