from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import logging
import traceback
import copy
import base64
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
    room_seq = fields.Char('Room Sequence')
    notes = fields.Text('Notes')


class ReservationTour(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.tour'
    _order = 'id DESC'
    _description = 'Rodex Model'

    tour_id = fields.Many2one('tt.master.tour', 'Tour Package')
    tour_id_str = fields.Text('Tour Package', compute='_compute_tour_id_str')
    booking_uuid = fields.Char('Booking UUID')

    room_ids = fields.One2many('tt.reservation.tour.room', 'booking_id', 'Rooms')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_tour_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})
    provider_booking_ids = fields.One2many('tt.provider.tour', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.tour', 'booking_id', string='Passengers')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_tour.tt_provider_type_tour'))
    payment_method_tour = fields.Selection(PAYMENT_METHOD, 'Tour Payment Method')
    installment_invoice_ids = fields.One2many('tt.installment.invoice', 'booking_id', 'Installments')
    is_already_issued = fields.Boolean('Already Issued', default=False)

    def get_form_id(self):
        return self.env.ref("tt_reservation_tour.tt_reservation_tour_form_view")

    @api.depends('tour_id')
    @api.onchange('tour_id')
    def _compute_tour_id_str(self):
        for rec in self:
            rec.tour_id_str = rec.tour_id and rec.tour_id.name or ''

    @api.depends('provider_booking_ids','provider_booking_ids.reconcile_line_id')
    def _compute_reconcile_state(self):
        for rec in self:
            reconcile_id_list = [rec1.reconcile_line_id.id != False for rec1 in rec.provider_booking_ids]
            if reconcile_id_list:
                if all(reconcile_id_list):
                    rec.reconcile_state = 'reconciled'
                elif any(reconcile_id_list):
                    rec.reconcile_state = 'partial'
                else:
                    rec.reconcile_state = 'not_reconciled'
            else:
                rec.reconcile_state = 'not_reconciled'

    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.calculate_service_charge()
            hold_date = datetime.now() + relativedelta(hours=6)
            self.action_booked_tour(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            self.action_issued_tour(acquirer_id and acquirer_id.id or False, customer_parent_id, context)
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            # refund
            self.action_refund()
        elif all(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.write({
                'state':  'fail_refunded',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif any(rec.state == 'issued' for rec in self.provider_booking_ids):
            # partial issued
            self.action_partial_issued_api_tour()
        elif any(rec.state == 'booked' for rec in self.provider_booking_ids):
            # partial booked
            self.action_partial_booked_api_tour(context, pnr_list, hold_date)
        elif all(rec.state == 'fail_issued' for rec in self.provider_booking_ids):
            # failed issue
            self.action_failed_issue()
        elif all(rec.state == 'fail_booked' for rec in self.provider_booking_ids):
            # failed book
            self.action_failed_book()
        elif all(rec.state == 'cancel' for rec in self.provider_booking_ids):
            # failed book
            self.action_set_as_cancel()
        elif self.provider_booking_ids:
            provider_obj = self.provider_booking_ids[0]
            self.write({
                'state': provider_obj.state,
            })
        else:
            self.write({
                'state': 'draft',
            })
            # raise RequestException(1006)

    def action_issued_tour(self,acquirer_id,customer_parent_id,context):
        if not context:  # Jika dari call from backend
            context = {
                'co_uid': self.env.user.id,
                'signature': ''
            }
        if not context.get('co_uid'):
            context.update({
                'co_uid': self.env.user.id
            })
        if not context.get('signature'):
            context.update({
                'signature': ''
            })

        if self.state != 'issued':
            pnr_list = []
            provider_list = []
            carrier_list = []
            for rec in self.provider_booking_ids:
                pnr_list.append(rec.pnr or '')
                provider_list.append(rec.provider_id.name or '')
                carrier_list.append(rec.carrier_id.name or '')

            self.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'] or self.env.user.id,
                'customer_parent_id': customer_parent_id,
                'pnr': ', '.join(pnr_list),
                'provider_name': ','.join(provider_list),
                'carrier_name': ','.join(carrier_list),
            })

            payment_method = self.payment_method_tour and self.payment_method_tour or 'full'
            if not self.is_already_issued:
                self.call_create_invoice(acquirer_id, context['co_uid'], customer_parent_id, payment_method)

            try:
                if self.agent_type_id.is_send_email_issued:
                    mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_tour')], limit=1)
                    if not mail_created:
                        temp_data = {
                            'provider_type': 'tour',
                            'order_number': self.name,
                            'type': 'issued',
                        }
                        temp_context = {
                            'co_agent_id': self.agent_id.id
                        }
                        self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                    else:
                        _logger.info('Issued email for {} is already created!'.format(self.name))
                        raise Exception('Issued email for {} is already created!'.format(self.name))
            except Exception as e:
                _logger.info('Error Create Email Queue')

    def call_create_invoice(self, acquirer_id, co_uid, customer_parent_id, payment_method):
        _logger.info('Creating Invoice for ' + self.name)

    def action_reissued(self):
        pax_amount = sum(1 for temp in self.passenger_ids if temp.pax_type != 'INF')
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

        pax_amount = sum(1 for temp in self.passenger_ids if temp.pax_type != 'INF')
        temp_seat = self.tour_id.seat
        temp_seat += pax_amount
        if temp_seat > self.tour_id.quota:
            temp_seat = self.tour_id.quota
        self.tour_id.sudo().write({
            'seat': temp_seat,
            'state': 'open'
        })
        for rec in self.tour_id.passengers_ids:
            if rec.booking_id.id == self.id:
                rec.sudo().write({
                    'master_tour_id': False
                })

    def action_partial_booked_api_tour(self,context,pnr_list,hold_date):
        self.write({
            'state': 'partial_booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now(),
            'hold_date': hold_date,
            'pnr': ','.join(pnr_list)
        })

    def action_partial_issued_api_tour(self):
        self.write({
            'state': 'partial_issued'
        })

    @api.multi
    def action_set_as_cancel(self):
        for rec in self:
            rec.write({
                'state': 'cancel',
                'cancel_date': datetime.now(),
                'cancel_uid': self.env.user.id
            })

            if rec.state != 'refund':
                pax_amount = sum(1 for temp in rec.passenger_ids if temp.pax_type != 'INF')
                temp_seat = rec.tour_id.seat
                temp_seat += pax_amount
                if temp_seat > rec.tour_id.quota:
                    temp_seat = rec.tour_id.quota
                rec.tour_id.sudo().write({
                    'seat': temp_seat,
                    'state': 'open'
                })
                for rec2 in rec.tour_id.passengers_ids:
                    if rec2.booking_id.id == rec.id:
                        rec2.sudo().write({
                            'master_tour_id': False
                        })

        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'

    def action_expired(self):
        self.state = 'cancel2'
        pax_amount = sum(1 for temp in self.passenger_ids if temp.pax_type != 'INF')
        temp_seat = self.tour_id.seat
        temp_seat += pax_amount
        if temp_seat > self.tour_id.quota:
            temp_seat = self.tour_id.quota
        self.tour_id.sudo().write({
            'seat': temp_seat,
            'state': 'open'
        })
        for rec in self.tour_id.passengers_ids:
            if rec.booking_id.id == self.id:
                rec.sudo().write({
                    'master_tour_id': False
                })
        try:
            for rec in self.provider_booking_ids.filtered(lambda x: x.state != 'cancel2'):
                rec.action_expired()
        except:
            _logger.error("provider type %s failed to expire vendor" % (self._name))

    def action_booked_tour(self,context,pnr_list,hold_date):
        if not context:  # Jika dari call from backend
            context = {
                'co_uid': self.env.user.id
            }
        if not context.get('co_uid'):
            context.update({
                'co_uid': self.env.user.id
            })

        if self.state != 'booked':
            write_values = {
                'state': 'booked',
                'pnr': ', '.join(pnr_list),
                'hold_date': hold_date,
                'booked_date': datetime.now(),
                'booked_uid': context['co_uid'] or self.env.user.id,
            }

            if write_values['pnr'] == '':
                write_values.pop('pnr')

            self.write(write_values)

            # Kurangi seat sejumlah pax_amount, lalu cek sisa kuota tour
            pax_amount = sum(1 for temp in self.passenger_ids if temp.pax_type != 'INF')  # jumlah orang yang di book
            temp_seat = self.tour_id.seat
            temp_seat -= pax_amount  # seat tersisa dikurangi jumlah orang yang di book
            temp_state = ''
            if temp_seat <= int(0.2 * self.tour_id.quota):
                temp_state = 'definite'  # pasti berangkat jika kuota >=80%
            if temp_seat == 0:
                temp_state = 'sold'  # kuota habis
            write_vals = {
                'seat': temp_seat
            }
            if temp_state:
                write_vals.update({
                    'state': temp_state
                })
            self.tour_id.sudo().write(write_vals)

            try:
                if self.agent_type_id.is_send_email_booked:
                    mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_tour')], limit=1)
                    if not mail_created:
                        temp_data = {
                            'provider_type': 'tour',
                            'order_number': self.name,
                            'type': 'booked',
                        }
                        temp_context = {
                            'co_agent_id': self.agent_id.id
                        }
                        self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                    else:
                        _logger.info('Booking email for {} is already created!'.format(self.name))
                        raise Exception('Booking email for {} is already created!'.format(self.name))
            except Exception as e:
                _logger.info('Error Create Email Queue')

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
            temp_provider_code = data.get('provider') and data['provider'] or 0
            temp_tour_code = data.get('tour_code') and data['tour_code'] or 0
            room_list = data.get('room_list') and data['room_list'] or []
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', temp_provider_code)], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            tour_data = self.env['tt.master.tour'].sudo().search([('tour_code', '=', temp_tour_code),('provider_id', '=', provider_obj.id)], limit=1)
            pricing = data.get('pricing') and data['pricing'] or []
            if not tour_data:
                raise RequestException(1004, additional_message='Tour not found. Please check your tour code.')
            tour_data = tour_data[0]
            pricelist_id = tour_data.id
            provider_id = tour_data.provider_id
            carrier_id = tour_data.carrier_id
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
                tour_room_code = temp_pax.get('tour_room_code', '')
                tour_room_obj = self.env['tt.master.tour.rooms'].sudo().search([('room_code', '=', tour_room_code)], limit=1)
                list_passenger_value[idx][2].update({
                    'customer_id': pax_ids[idx].id,
                    'title': temp_pax['title'],
                    'pax_type': temp_pax['pax_type'],
                    'tour_room_id': tour_room_obj and tour_room_obj[0].id or False,
                    'tour_room_seq': temp_pax.get('tour_room_seq', ''),
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
                'contact_phone': contact_data.get('mobile') and str(contact_data['calling_code']) +" - "+ str(
                    contact_data['mobile']),
                'agent_id': context['co_agent_id'],
                'user_id': context['co_uid'],
                'tour_id': pricelist_id,
                'adult': data.get('adult') and int(data['adult']) or 0,
                'child': data.get('child') and int(data['child']) or 0,
                'infant': data.get('infant') and int(data['infant']) or 0,
                'departure_date': tour_data.departure_date,
                'arrival_date': tour_data.arrival_date,
                'provider_name': provider_id.name,
                'transport_type': 'tour',
            })

            if booking_obj:
                for room in room_list:
                    room_obj = self.env['tt.master.tour.rooms'].sudo().search([('room_code', '=', room['room_code'])], limit=1)
                    room.update({
                        'booking_id': booking_obj.id,
                        'room_id': room_obj and room_obj[0].id or False
                    })
                    self.env['tt.reservation.tour.room'].sudo().create(room)

                balance_due = 0
                for temp_sc in pricing:
                    if temp_sc['charge_type'] not in ['ROC', 'RAC']:
                        balance_due += temp_sc['pax_count'] * temp_sc['amount']

                provider_tour_vals = {
                    'booking_id': booking_obj.id,
                    'tour_id': pricelist_id,
                    'provider_id': provider_id.id,
                    'carrier_id': carrier_id.id,
                    'carrier_code': carrier_id.code,
                    'carrier_name': carrier_id.name,
                    'departure_date': tour_data.departure_date,
                    'arrival_date': tour_data.arrival_date,
                    'balance_due': balance_due,
                    'total_price': balance_due,
                    'sequence': 1
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

                provider_booking_list = []
                for prov in booking_obj.provider_booking_ids:
                    provider_booking_list.append(prov.to_dict())
                response = booking_obj.to_dict()
                response.update({
                    'provider_booking': provider_booking_list
                })
            else:
                response = {
                    'book_id': 0,
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
            if data.get('order_id'):
                book_obj = self.env['tt.reservation.tour'].sudo().browse(int(data['order_id']))
            else:
                book_objs = self.env['tt.reservation.tour'].sudo().search([('name', '=', data['order_number'])], limit=1)
                book_obj = book_objs[0]

            payment_method = data.get('payment_method') and data['payment_method'] or 'full'
            vals = {
                'payment_method_tour': payment_method
            }
            book_obj.sudo().write(vals)

            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict()
            response.update({
                'provider_booking': provider_booking_list
            })
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def payment_tour_api(self,req,context):
        return self.payment_reservation_api('tour',req,context)

    def get_booking_for_vendor_by_api(self, data, context, **kwargs):
        try:
            search_booking_num = data['order_number']
            book_obj = self.env['tt.reservation.tour'].sudo().search([('name', '=', search_booking_num)], limit=1)
            if book_obj:
                book_obj = book_obj[0]
            master = self.env['tt.master.tour'].browse(book_obj.tour_id.id)

            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict()
            response.update({
                'provider_booking': provider_booking_list,
                'booking_uuid': book_obj.booking_uuid and book_obj.booking_uuid or False,
            })
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def get_booking_api(self, data, context, **kwargs):
        try:
            search_booking_num = data['order_number']
            book_obj = self.env['tt.reservation.tour'].sudo().search([('name', '=', search_booking_num)], limit=1)
            if book_obj:
                book_obj = book_obj[0]
                if book_obj.agent_id.id != context.get('co_agent_id', -1):
                    raise RequestException(1001)
                master = self.env['tt.master.tour'].browse(book_obj.tour_id.id)
                image_urls = []
                for img in master.image_ids:
                    image_urls.append(str(img.url))

                tour_package = {
                    'id': master.id,
                    'name': master.name,
                    'duration': master.duration,
                    'departure_date': master.departure_date,
                    'arrival_date': master.arrival_date,
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
                        'room_code': room_data.room_id.room_code,
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

                payment_rules = [
                    {
                        'name': 'Down Payment',
                        'description': 'Down Payment',
                        'payment_percentage': book_obj.tour_id.down_payment,
                        'due_date': date.today(),
                        'is_dp': True
                    }
                ]
                for payment in book_obj.tour_id.payment_rules_ids:
                    temp_pay = {
                        'name': payment.name,
                        'description': payment.description,
                        'payment_percentage': payment.payment_percentage,
                        'due_date': payment.due_date,
                        'is_dp': False
                    }
                    payment_rules.append(temp_pay)

                if data.get('state'):
                    book_update_vals = {
                        'state': data['state']
                    }
                    if book_obj.state == 'issued':
                        book_update_vals.update({
                            'is_already_issued': True
                        })
                    book_obj.sudo().write(book_update_vals)
                    self.env.cr.commit()

                provider_booking_list = []
                for prov in book_obj.provider_booking_ids:
                    provider_booking_list.append(prov.to_dict())
                response = book_obj.to_dict()
                response.update({
                    'provider_booking': provider_booking_list,
                    'passengers': passengers,
                    'booking_uuid': book_obj.booking_uuid and book_obj.booking_uuid or False,
                    'tour_details': tour_package,
                    'rooms': rooms,
                    'payment_rules': payment_rules,
                    'grand_total': book_obj.total,
                })
                return ERR.get_no_error(response)
            else:
                raise RequestException(1001)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def update_booking_api(self, data, context, **kwargs):
        try:
            if data.get('order_id'):
                book_obj = self.env['tt.reservation.tour'].sudo().browse(int(data['order_id']))
            else:
                book_objs = self.env['tt.reservation.tour'].sudo().search([('name', '=', data['order_number'])], limit=1)
                book_obj = book_objs[0]

            book_info = data.get('book_info') and data['book_info'] or {}

            if book_info['status'] == 'booked':
                write_vals = {
                    'sid_booked': context.get('sid') and context['sid'] or '',
                    'booking_uuid': book_info.get('booking_uuid') and book_info['booking_uuid'] or ''
                }

                pnr_list = []
                for rec in book_obj.provider_booking_ids:
                    rec.action_booked_api_tour(book_info, context)
                    pnr_list.append(book_info.get('pnr') or '')

                book_obj.check_provider_state(context, pnr_list)
                book_obj.sudo().write(write_vals)
            elif book_info['status'] == 'issued':
                for rec in book_obj.provider_booking_ids:
                    rec.action_issued_api_tour(context)

                book_obj.check_provider_state(context, req=data)
            self.env.cr.commit()

            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict()
            response.update({
                'provider_booking': provider_booking_list,
                'booking_uuid': book_obj.booking_uuid and book_obj.booking_uuid or False,
            })
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1005)

    def get_nta_amount(self,method = 'full'):
        if method == 'installment':
            return (self.tour_id.down_payment / 100) * self.agent_nta
        else:
            return super(ReservationTour, self).get_nta_amount()

    def get_total_amount(self,method = 'full'):
        if method == 'installment':
            return (self.tour_id.down_payment / 100) * self.total
        else:
            return super(ReservationTour, self).get_total_amount()

    @api.multi
    def print_ho_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        tour_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_tour')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = tour_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = tour_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Tour HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Tour HO Invoice',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_ho_invoice_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_ho_invoice_id.url,
        }
        return url
        # return tour_ho_invoice_id.report_action(self, data=datas)

    def print_itinerary(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.tour'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        tour_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_tour')

        if not book_obj.printout_itinerary_id:
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = tour_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = tour_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Tour Itinerary %s.pdf' % book_obj.name,
                    'file_reference': 'Tour Itinerary',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.printout_itinerary_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Tour Itinerary",
            'target': 'new',
            'url': book_obj.printout_itinerary_id.url,
        }
        return url

    def get_aftersales_desc(self):
        desc_txt = 'PNR: ' + self.pnr + '<br/>'
        desc_txt += 'Tour: ' + self.tour_id.name + '<br/>'
        desc_txt += 'Category: ' + dict(self.tour_id._fields['tour_category'].selection).get(self.tour_id.tour_category) + ' - ' + dict(self.tour_id._fields['tour_type'].selection).get(self.tour_id.tour_type) + '<br/>'
        desc_txt += 'Departure Date: ' + datetime.strptime(self.departure_date, '%Y-%m-%d').strftime('%d %b %Y') + '<br/>'
        desc_txt += 'Arrival Date: ' + datetime.strptime(self.arrival_date, '%Y-%m-%d').strftime('%d %b %Y') + '<br/>'
        return desc_txt
