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
    _description = 'Reservation Tour Room'

    booking_id = fields.Many2one('tt.reservation.tour', 'Reservation Tour')
    room_id = fields.Many2one('tt.master.tour.rooms', 'Room')
    room_seq = fields.Char('Room Sequence')
    notes = fields.Text('Notes')


class ReservationTour(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.tour'
    _order = 'id DESC'
    _description = 'Reservation Tour'

    tour_lines_id = fields.Many2one('tt.master.tour.lines', 'Tour Line')
    tour_id = fields.Many2one('tt.master.tour', 'Tour Package', related='tour_lines_id.master_tour_id', store=True)
    tour_id_str = fields.Text('Tour Package', compute='_compute_tour_id_str')
    booking_uuid = fields.Char('Booking UUID')

    room_ids = fields.One2many('tt.reservation.tour.room', 'booking_id', 'Rooms')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_tour_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})
    provider_booking_ids = fields.One2many('tt.provider.tour', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.tour', 'booking_id', string='Passengers')

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_tour.tt_provider_type_tour'))
    payment_method_tour = fields.Selection(PAYMENT_METHOD, 'Tour Payment Method')
    installment_invoice_ids = fields.One2many('tt.installment.invoice', 'booking_id', 'Installments')

    def get_form_id(self):
        return self.env.ref("tt_reservation_tour.tt_reservation_tour_form_view")

    @api.depends("passenger_ids.channel_service_charge_ids")
    def _compute_total_channel_upsell(self):
        for rec in self:
            chan_upsell_total = 0
            for pax in rec.passenger_ids:
                for csc in pax.channel_service_charge_ids:
                    chan_upsell_total += csc.amount
            rec.total_channel_upsell = chan_upsell_total

    @api.depends('tour_id')
    @api.onchange('tour_id')
    def _compute_tour_id_str(self):
        for rec in self:
            rec.tour_id_str = rec.tour_id and rec.tour_id.name or ''

    @api.depends('provider_booking_ids', 'provider_booking_ids.reconcile_line_id')
    def _compute_reconcile_state(self):
        for rec in self:
            if all([rec1.reconcile_line_id and rec1.reconcile_line_id.state == 'match' or False for rec1 in
                    rec.provider_booking_ids]):
                rec.reconcile_state = 'reconciled'
            elif any([rec1.reconcile_line_id and rec1.reconcile_line_id.state == 'match' or False for rec1 in
                      rec.provider_booking_ids]):
                rec.reconcile_state = 'partial'
            elif all([rec1.reconcile_line_id and rec1.reconcile_line_id.state == 'cancel' or False for rec1 in
                      rec.provider_booking_ids]):
                rec.reconcile_state = 'cancel'
            else:
                rec.reconcile_state = 'not_reconciled'

    def get_master_tour_hold_date(self):
        temp_add_hours = 100
        for rec in self.provider_booking_ids:
            if rec.tour_id.hold_date_timer:
                add_hours = rec.tour_id.hold_date_timer
            else:
                add_hours = int(self.env['ir.config_parameter'].get_param('tt_master_tour.master_tour_default_hold_date_timer'))
            if add_hours <= temp_add_hours:
                temp_add_hours = add_hours
        final_add_hours = temp_add_hours >= 100 and 6 or temp_add_hours
        return datetime.now() + relativedelta(hours=final_add_hours)

    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.calculate_service_charge()
            if not hold_date:
                hold_date = self.get_master_tour_hold_date()
            self.action_booked_tour(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)

            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued_api_tour(issued_req, context)
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            # refund
            self.action_refund()
        elif all(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.action_reverse_tour(context)
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

    def action_issued_tour(self,data):
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
                'issued_uid': data.get('co_uid', self.env.user.id),
                'customer_parent_id': data['customer_parent_id'],
                'pnr': ', '.join(pnr_list),
                'provider_name': ','.join(provider_list),
                'carrier_name': ','.join(carrier_list),
            })

            try:
                if self.agent_type_id.is_send_email_issued:
                    mail_created = self.env['tt.email.queue'].with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_tour')], limit=1)
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

    def action_issued_api_tour(self,req,context):
        data = {
            'co_uid': context['co_uid'],
            'customer_parent_id': req['customer_parent_id'],
            'acquirer_id': req['acquirer_id'],
            'payment_reference': req.get('payment_reference', ''),
            'payment_ref_attachment': req.get('payment_ref_attachment', []),
        }
        self.action_issued_tour(data)

    def call_create_invoice(self, acquirer_id, co_uid, customer_parent_id, payment_method):
        _logger.info('Creating Invoice for ' + self.name)

    def action_refund(self):
        self.write({
            'state': 'refund',
            'refund_date': datetime.now(),
            'refund_uid': self.env.user.id
        })
        # self.message_post(body='Order REFUNDED')

        pax_amount = sum(1 for temp in self.passenger_ids if temp.pax_type != 'INF')
        self.tour_lines_id.cancel_book_line_quota(pax_amount)
        for rec in self.tour_id.passengers_ids:
            if rec.booking_id.id == self.id:
                rec.write({
                    'master_tour_id': False,
                    'master_tour_line_id': False
                })

    def action_reverse_tour(self,context):
        self.write({
            'state':  'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
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
                rec.tour_lines_id.cancel_book_line_quota(pax_amount)
                for rec2 in rec.tour_id.passengers_ids:
                    if rec2.booking_id.id == rec.id:
                        rec2.write({
                            'master_tour_id': False,
                            'master_tour_line_id': False
                        })

        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'

    def action_expired(self):
        self.state = 'cancel2'
        pax_amount = sum(1 for temp in self.passenger_ids if temp.pax_type != 'INF')
        self.tour_lines_id.cancel_book_line_quota(pax_amount)
        for rec in self.tour_id.passengers_ids:
            if rec.booking_id.id == self.id:
                rec.write({
                    'master_tour_id': False,
                    'master_tour_line_id': False
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
            self.tour_lines_id.book_line_quota(pax_amount)

            try:
                if self.agent_type_id.is_send_email_booked:
                    mail_created = self.env['tt.email.queue'].with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_tour')], limit=1)
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
            for idy, p_sc in enumerate(provider.cost_service_charge_ids):
                p_charge_code = p_sc.charge_code
                p_charge_type = p_sc.charge_type
                p_pax_type = p_sc.pax_type
                c_code = ''
                c_type = ''
                if not sc_value.get(p_pax_type):
                    sc_value[p_pax_type] = {}
                if p_charge_type != 'RAC':
                    if 'csc' in p_charge_code.split('.'):
                        c_type = "%s%s" % (p_charge_code, p_charge_type.lower())
                        sc_value[p_pax_type][c_type] = {
                            'amount': 0,
                            'foreign_amount': 0,
                            'pax_count': p_sc.pax_count,  ## ini asumsi yang pertama yg plg benar pax countnya
                            'total': 0
                        }
                        c_code = p_charge_code
                    elif not sc_value[p_pax_type].get(p_charge_type):
                        c_type = "%s%s" % (p_charge_type, idy) ## untuk service charge yg kembar contoh SSR
                        sc_value[p_pax_type][c_type] = {
                            'amount': 0,
                            'foreign_amount': 0,
                            'pax_count': p_sc.pax_count,  ## ini asumsi yang pertama yg plg benar pax countnya
                            'total': 0
                        }
                    if not c_code:
                        c_code = p_charge_type.lower()
                    if not c_type:
                        c_type = p_charge_type
                elif p_charge_type == 'RAC':
                    if not sc_value[p_pax_type].get(p_charge_code):
                        sc_value[p_pax_type][p_charge_code] = {}
                        sc_value[p_pax_type][p_charge_code].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'pax_count': p_sc.pax_count,  ## ini asumsi yang pertama yg plg benar pax countnya
                            'total': 0
                        })
                    c_type = p_charge_code
                    c_code = p_charge_code
                sc_value[p_pax_type][c_type].update({
                    'charge_type': p_charge_type,
                    'charge_code': c_code,
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
                    curr_dict['ho_id'] = self.ho_id.id if self.ho_id else ''
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
            passengers_data = copy.deepcopy(data['passengers_data'])  # waktu create passenger fungsi odoo field kosong di hapus cth: work_place
            temp_provider_code = data.get('provider') and data['provider'] or 0
            temp_tour_code = data.get('tour_code') and data['tour_code'] or ''
            temp_tour_line_code = data.get('tour_line_code') and data['tour_line_code'] or ''
            room_list = data.get('room_list') and data['room_list'] or []
            provider_obj = self.env['tt.provider'].search([('code', '=', temp_provider_code)], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            tour_data = self.env['tt.master.tour'].search([('tour_code', '=', provider_obj.alias + '~' + temp_tour_code),('provider_id', '=', provider_obj.id)], limit=1)
            pricing = data.get('pricing') and data['pricing'] or []
            if not tour_data:
                raise RequestException(1004, additional_message='Tour not found. Please check your tour code.')
            tour_data = tour_data[0]
            tour_line_data = self.env['tt.master.tour.lines'].search([('tour_line_code', '=', temp_tour_line_code), ('master_tour_id', '=', tour_data.id)])
            pricelist_id = tour_data.id
            provider_id = tour_data.provider_id
            carrier_id = tour_data.carrier_id
            total_all_pax = int(data.get('adult')) + int(data.get('child')) + int(data.get('infant'))
            if tour_line_data.seat - total_all_pax < 0:
                raise RequestException(1004, additional_message='Not enough seats. Seats available: %s/%s' % (tour_line_data.seat, tour_line_data.quota,))

            booker_obj = self.create_booker_api(booker_data, context)
            contact_data = contacts_data[0]
            contact_objs = []
            for con in contacts_data:
                contact_objs.append(self.create_contact_api(con, booker_obj, context))

            contact_obj = contact_objs[0]

            list_passenger_value = self.create_passenger_value_api(passengers)
            pax_ids = self.create_customer_api(passengers, context, booker_obj.seq_id, contact_obj.seq_id)

            for idx, temp_pax in enumerate(passengers):
                tour_room_code = temp_pax.get('tour_room_code', '')
                tour_room_obj = self.env['tt.master.tour.rooms'].search([('room_code', '=', tour_room_code)], limit=1)
                list_passenger_value[idx][2].update({
                    'customer_id': pax_ids[idx].id,
                    'title': temp_pax['title'],
                    'pax_type': temp_pax['pax_type'],
                    'tour_room_id': tour_room_obj and tour_room_obj[0].id or False,
                    'tour_room_seq': temp_pax.get('tour_room_seq', ''),
                    'master_tour_id': tour_data and tour_data.id or False,
                    'master_tour_line_id': tour_line_data and tour_line_data.id or False
                })
                if passengers_data[idx].get('description'):
                    list_passenger_value[idx][2].update({
                        "description": passengers_data[idx]['description']
                    })

            try:
                agent_obj = self.env['tt.customer'].browse(int(booker_obj.id)).agent_id
                if not agent_obj:
                    agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            except Exception:
                agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id

            if tour_data.tour_type_id.is_open_date:
                if not data.get('departure_date'):
                    raise RequestException(1004, additional_message='Departure Date parameter is required for Open Trip!')
                dept_day_name = datetime.strptime(data['departure_date'], '%Y-%m-%d').strftime("%A")
                if dept_day_name in tour_line_data.get_restricted_days():
                    raise RequestException(1004, additional_message='Departure day cannot be on %s. Please choose another date!' % dept_day_name)
                temp_dept_date = data['departure_date']
                temp_arr_date = (datetime.strptime(data['departure_date'], '%Y-%m-%d') + timedelta(days=int(tour_data.duration-1))).strftime('%Y-%m-%d')
                if temp_dept_date < tour_line_data.departure_date.strftime('%Y-%m-%d') or temp_arr_date > tour_line_data.arrival_date.strftime('%Y-%m-%d'):
                    raise RequestException(1004, additional_message='Tour cannot start before or end after the designated period. Please check your Departure Date parameter!')
            else:
                temp_dept_date = tour_line_data.departure_date
                temp_arr_date = tour_line_data.arrival_date

            ## 22 JUN 2023 - IVAN
            ## GET CURRENCY CODE
            currency = ''
            currency_obj = None
            for svc in pricing:
                currency = svc['currency']
            if currency:
                currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
                # if currency_obj:
                #     book_obj.currency_id = currency_obj.id

            booking_obj = self.create({
                'contact_id': contact_obj.id,
                'booker_id': booker_obj.id,
                'passenger_ids': list_passenger_value,
                'contact_title': contact_data['title'],
                'contact_name': contact_data['first_name'] + ' ' + contact_data['last_name'],
                'contact_email': contact_data.get('email') and contact_data['email'] or '',
                'contact_phone': contact_data.get('mobile') and str(contact_data['calling_code']) +" - "+ str(
                    contact_data['mobile']),
                'ho_id': context['co_ho_id'],
                'agent_id': context['co_agent_id'],
                'customer_parent_id': context.get('co_customer_parent_id',False),
                'user_id': context['co_uid'],
                'tour_id': pricelist_id,
                'tour_lines_id': tour_line_data.id,
                'adult': data.get('adult') and int(data['adult']) or 0,
                'child': data.get('child') and int(data['child']) or 0,
                'infant': data.get('infant') and int(data['infant']) or 0,
                'departure_date': temp_dept_date,
                'arrival_date': temp_arr_date,
                'provider_name': provider_id.name,
                'transport_type': 'tour',
                'currency_id': currency_obj.id if currency and currency_obj else self.env.user.company_id.currency_id.id
            })

            if booking_obj:
                for room in room_list:
                    room_obj = self.env['tt.master.tour.rooms'].search([('room_code', '=', room['room_code'])], limit=1)
                    room.update({
                        'booking_id': booking_obj.id,
                        'room_id': room_obj and room_obj[0].id or False
                    })
                    self.env['tt.reservation.tour.room'].create(room)

                balance_due = 0
                for temp_sc in pricing:
                    if temp_sc['charge_type'] not in ['ROC', 'RAC']:
                        balance_due += temp_sc['pax_count'] * temp_sc['amount']

                provider_tour_vals = {
                    'booking_id': booking_obj.id,
                    'tour_id': pricelist_id,
                    'tour_lines_id': tour_line_data.id,
                    'provider_id': provider_id.id,
                    'carrier_id': carrier_id.id,
                    'carrier_code': carrier_id.code,
                    'carrier_name': carrier_id.name,
                    'departure_date': temp_dept_date,
                    'arrival_date': temp_arr_date,
                    'balance_due': balance_due,
                    'total_price': balance_due,
                    'sequence': 1
                }

                provider_tour_obj = self.env['tt.provider.tour'].create(provider_tour_vals)
                for psg in booking_obj.passenger_ids:
                    vals = {
                        'provider_id': provider_tour_obj.id,
                        'passenger_id': psg.id,
                        'pax_type': psg.pax_type,
                        'tour_room_id': psg.tour_room_id.id
                    }
                    self.env['tt.ticket.tour'].create(vals)
                provider_tour_obj.delete_service_charge()
                provider_tour_obj.create_service_charge(pricing)

                provider_booking_list = []
                for prov in booking_obj.provider_booking_ids:
                    provider_booking_list.append(prov.to_dict())
                response = booking_obj.to_dict(context)
                response.update({
                    'provider_booking': provider_booking_list
                })

                ## PAKAI VOUCHER
                if data.get('voucher'):
                    booking_obj.add_voucher(data['voucher']['voucher_reference'], context)
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
            if data.get('book_id'):
                book_obj = self.env['tt.reservation.tour'].browse(int(data['book_id']))
            else:
                book_objs = self.env['tt.reservation.tour'].search([('name', '=', data['order_number'])], limit=1)
                book_obj = book_objs[0]

            payment_method = data.get('payment_method') and data['payment_method'] or 'full'
            vals = {
                'payment_method_tour': payment_method
            }
            book_obj.write(vals)

            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict(context)
            response.update({
                'provider_booking': provider_booking_list,
                'booking_uuid': book_obj.booking_uuid and book_obj.booking_uuid or False
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
            book_obj = self.env['tt.reservation.tour'].search([('name', '=', search_booking_num)], limit=1)
            if book_obj:
                book_obj = book_obj[0]
            master = self.env['tt.master.tour'].browse(book_obj.tour_id.id)

            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict(context)
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
        book_obj = self.get_book_obj(data.get('book_id'), data.get('order_number'))
        try:
            book_obj.create_date
        except:
            raise RequestException(1001)

        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        # if book_obj.agent_id.id == context.get('co_agent_id',-1) or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids:
        # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
        _co_user = self.env['res.users'].browse(int(context['co_uid']))
        if book_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_erp_manager'):
            image_urls = []
            for img in book_obj.tour_id.image_ids:
                image_urls.append(str(img.url))

            tour_package = {
                'name': book_obj.tour_id.name,
                'duration': book_obj.tour_id.duration,
                'departure_date': book_obj.tour_lines_id.departure_date,
                'arrival_date': book_obj.tour_lines_id.arrival_date,
                'tour_category': book_obj.tour_id.tour_category,
                'tour_type': book_obj.tour_id.tour_type_id.to_dict(),
                'tour_type_str': book_obj.tour_id.tour_type_id.name,
                'image_urls': image_urls,
                'flight_segments': book_obj.tour_id.get_flight_segment(),
                'itinerary_ids': book_obj.tour_id.get_itineraries(),
                'other_infos': book_obj.tour_id.get_tour_other_info()
            }

            passengers = []
            for rec in book_obj.passenger_ids:
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
                    'room_hotel': room_data.room_id.hotel and room_data.room_id.hotel or '',
                    'room_desc': room_data.room_id.description and room_data.room_id.description or '-',
                    'room_notes': room_data.notes and room_data.notes or '-'
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
                    'payment_percentage': book_obj.tour_lines_id.down_payment,
                    'due_date': date.today(),
                    'is_dp': True
                }
            ]
            for payment in book_obj.tour_lines_id.payment_rules_ids:
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

                book_obj.write(book_update_vals)
                self.env.cr.commit()

            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict(context)
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
            raise RequestException(1035)

    def update_booking_api(self, data, context, **kwargs):
        try:
            if data.get('book_id'):
                book_obj = self.env['tt.reservation.tour'].browse(int(data['book_id']))
            else:
                book_objs = self.env['tt.reservation.tour'].search([('name', '=', data['order_number'])], limit=1)
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
                book_obj.write(write_vals)
            elif book_info['status'] == 'issued':
                for rec in book_obj.provider_booking_ids:
                    rec.action_issued_api_tour(context)

                book_obj.check_provider_state(context, req=data)
            self.env.cr.commit()

            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict(context)
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
            return (self.tour_lines_id.down_payment / 100) * self.agent_nta
        else:
            return super(ReservationTour, self).get_nta_amount()

    def get_total_amount(self,method = 'full'):
        if method == 'installment':
            return (self.tour_lines_id.down_payment / 100) * self.total
        else:
            return super(ReservationTour, self).get_total_amount()

    # DEPRECATED
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

        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
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

    def print_itinerary_price(self, data, ctx=None):
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
        datas['is_with_price'] = True
        tour_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_tour')

        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
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
                    'filename': 'Tour Itinerary %s (Price).pdf' % book_obj.name,
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
            book_obj.printout_itinerary_price_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Tour Itinerary",
            'target': 'new',
            'url': book_obj.printout_itinerary_price_id.url,
        }
        return url

    def get_aftersales_desc(self):
        desc_txt = 'PNR: ' + self.pnr + '<br/>'
        desc_txt += 'Tour: ' + self.tour_id.name + '<br/>'
        desc_txt += 'Category: ' + dict(self.tour_id._fields['tour_category'].selection).get(self.tour_id.tour_category) + ' - ' + self.tour_id.tour_type_id.name + '<br/>'
        desc_txt += 'Departure Date: ' + datetime.strptime(self.departure_date, '%Y-%m-%d').strftime('%d %b %Y') + '<br/>'
        desc_txt += 'Arrival Date: ' + datetime.strptime(self.arrival_date, '%Y-%m-%d').strftime('%d %b %Y') + '<br/>'
        return desc_txt

    def get_passenger_pricing_breakdown(self):
        pax_list = []
        for rec in self.passenger_ids:
            pax_data = {
                'passenger_name': '%s %s' % (rec.title, rec.name),
                'pnr_list': []
            }
            for rec2 in self.provider_booking_ids:
                pax_ticketed = False
                for rec3 in rec2.ticket_ids.filtered(lambda x: x.passenger_id.id == rec.id):
                    pax_ticketed = True
                pax_pnr_data = {
                    'pnr': rec2.pnr,
                    'ticket_number': '',
                    'currency_code': rec2.currency_id and rec2.currency_id.name or '',
                    'provider': rec2.provider_id and rec2.provider_id.name or '',
                    'carrier_name': self.carrier_name or '',
                    'agent_nta': 0,
                    'agent_commission': 0,
                    'parent_agent_commission': 0,
                    'ho_nta': 0,
                    'ho_commission': 0,
                    'total_commission': 0,
                    'upsell': 0,
                    'discount': 0,
                    'fare': 0,
                    'tax': 0,
                    'grand_total': 0
                }
                for rec3 in rec2.cost_service_charge_ids.filtered(lambda y: rec.id in y.passenger_tour_ids.ids):
                    pax_pnr_data['ho_nta'] += rec3.amount
                    if rec3.charge_type == 'RAC' and rec3.charge_code == 'rac':
                        pax_pnr_data['agent_commission'] -= rec3.amount
                        pax_pnr_data['agent_nta'] += rec3.amount
                    if rec3.charge_type == 'RAC':
                        pax_pnr_data['total_commission'] -= rec3.amount
                        if rec3.commission_agent_id.is_ho_agent:
                            pax_pnr_data['ho_commission'] -= rec3.amount
                    if rec3.charge_type != 'RAC':
                        pax_pnr_data['grand_total'] += rec3.amount
                        pax_pnr_data['agent_nta'] += rec3.amount
                    if rec3.charge_type == 'FARE':
                        pax_pnr_data['fare'] += rec3.amount
                    if rec3.charge_type == 'TAX':
                        pax_pnr_data['tax'] += rec3.amount
                    if rec3.charge_type == 'ROC':
                        pax_pnr_data['upsell'] += rec3.amount
                    if rec3.charge_type == 'DISC':
                        pax_pnr_data['discount'] -= rec3.amount
                pax_pnr_data['parent_agent_commission'] = pax_pnr_data['total_commission'] - pax_pnr_data[
                    'agent_commission'] - pax_pnr_data['ho_commission']
                if pax_ticketed:
                    pax_data['pnr_list'].append(pax_pnr_data)
            pax_list.append(pax_data)
        return pax_list
