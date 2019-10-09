from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import logging
import traceback
import copy
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools.api import Response

# from Ap
_logger = logging.getLogger(__name__)

PAYMENT_METHOD = [
    ('full', 'Full Payment'),
    ('installment', 'Installment')
]


class ReservationTour(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.tour'
    _description = 'Rodex Model'

    tour_id = fields.Many2one('tt.master.tour', 'Tour ID')
    # tour_id = fields.Char('Tour ID')

    next_installment_date = fields.Date('Next Due Date', compute='_next_installment_date', store=True)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_tour_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})
    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger',
                                 domain=[('res_model', '=', 'tt.reservation.tour')])
    provider_booking_ids = fields.One2many('tt.provider.tour', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.tour', 'booking_id', string='Passengers')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_tour.tt_provider_type_tour'))
    payment_method = fields.Selection(PAYMENT_METHOD, 'Payment Method')

    def action_issued_tour(self,co_uid,customer_parent_id,acquirer_id=False):
        if self.state != 'issued':
            self.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': self.env.user.id
            })
            for rec in self.provider_booking_ids:
                rec.action_create_ledger()

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
        self.tour_id.state_tour = 'open'

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
            self.tour_id.state_tour = 'open'

        for rec in self.tour_id.passengers_ids:
            if rec.tour_id.id == self.id:
                rec.sudo().tour_pricelist_id = False
    # *END STATE*

    def action_booked_tour(self, api_context=None):
        if self.state != 'booked':
            self.write({
                'state': 'booked',
                'booked_date': datetime.now(),
                'booked_uid': self.env.user.id,
                'hold_date': datetime.now() + relativedelta(days=1),
            })

        # Kurangi seat sejumlah pax_amount, lalu cek sisa kuota tour
        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')  # jumlah orang yang di book
        self.tour_id.seat -= pax_amount  # seat tersisa dikurangi jumlah orang yang di book
        if self.tour_id.seat <= int(0.2 * self.tour_id.quota):
            self.tour_id.state_tour = 'definite'  # pasti berangkat jika kuota >=80%
        if self.tour_id.seat == 0:
            self.tour_id.state_tour = 'sold'  # kuota habis

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

    # def test_booking(self):
    # self.create_booking(self.contact_data, self.passenger_data, self.option, self.search_request, '', self.context, self.kwargs)

    def _validate_tour(self, data, type):
        list_data = []
        if type == 'context':
            list_data = ['co_uid', 'is_company_website']
        elif type == 'header':
            list_data = ['adult', 'child', 'infant']

        keys_data = []
        for rec in data.iterkeys():
            keys_data.append(str(rec))

        for ls in list_data:
            if not ls in keys_data:
                raise Exception('ERROR Validate %s, key : %s' % (type, ls))
        return True

    def update_api_context(self, customer_parent_id, context):
        context['co_uid'] = int(context['co_uid'])
        user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
        if context['is_company_website']:
            # ============================================
            # ====== Context dari WEBSITE/FRONTEND =======
            # ============================================
            if user_obj.agent_id.agent_type_id.id in \
                    (self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
                # ===== COR/POR User =====
                context.update({
                    'agent_id': user_obj.agent_id.parent_agent_id.id,
                    'customer_parent_id': user_obj.agent_id.id,
                    'booker_type': 'COR/POR',
                })
            elif customer_parent_id:
                # ===== COR/POR in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'customer_parent_id': customer_parent_id,
                    'booker_type': 'COR/POR',
                })
            else:
                # ===== FPO in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'customer_parent_id': user_obj.agent_id.id,
                    'booker_type': 'FPO',
                })
        else:
            # ===============================================
            # ====== Context dari API Client ( BTBO ) =======
            # ===============================================
            context.update({
                'agent_id': user_obj.agent_id.id,
                'customer_parent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
            })
        return context

    def commit_booking_api(self, data, context, **kwargs):
        try:
            booking_data = data.get('booking_data')
            price_itinerary = {}
            tour_data = {}
            pricelist_id = 0
            if booking_data:
                tour_data = booking_data.get('tour_data')
                pricelist_id = tour_data.get('id') and int(tour_data['id']) or 0
                price_itinerary = booking_data.get('price_itinerary')
            force_issued = data.get('force_issued') and int(data['force_issued']) or 0
            booker_id = data.get('booker_id') and data['booker_id'] or False
            contact_id = data.get('contact_id') and data['contact_id'] or False
            pax_ids = data.get('pax_ids') and data['pax_ids'] or []
            try:
                agent_obj = self.env['tt.customer'].browse(int(booker_id)).agent_id
                if not agent_obj:
                    agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            except Exception:
                agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id

            service_charge = []
            service_charge_ids = []
            def_currency = self.env['res.currency'].search([('name', '=', 'IDR')])[0].id

            if price_itinerary.get('adult_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'fare',
                    'charge_type': 'fare',
                    'amount': price_itinerary['adult_price'] / price_itinerary['adult_amount'],
                    'pax_count': price_itinerary['adult_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Adult Price',
                })
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['airport_tax_total'] / (price_itinerary['adult_amount'] + price_itinerary['child_amount'] + price_itinerary['infant_amount']),
                    'pax_count': price_itinerary['adult_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Airport Tax',
                })

            if price_itinerary.get('adult_surcharge_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['adult_surcharge_price'] / price_itinerary['adult_surcharge_amount'],
                    'pax_count': price_itinerary['adult_surcharge_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Adult Surcharge',
                })

            if price_itinerary.get('single_supplement_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['single_supplement_price'] / price_itinerary['single_supplement_amount'],
                    'pax_count': price_itinerary['single_supplement_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Single Supplement',
                })

            if price_itinerary.get('tipping_guide_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['tipping_guide_total'] / price_itinerary['tipping_guide_amount'],
                    'pax_count': price_itinerary['tipping_guide_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Tipping Tour Guide',
                })

            if price_itinerary.get('tipping_tour_leader_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['tipping_tour_leader_total'] / price_itinerary['tipping_tour_leader_amount'],
                    'pax_count': price_itinerary['tipping_tour_leader_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Tipping Tour Leader',
                })

            if price_itinerary.get('tipping_driver_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['tipping_driver_total'] / price_itinerary['tipping_driver_amount'],
                    'pax_count': price_itinerary['tipping_driver_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Tipping Driver',
                })

            if price_itinerary.get('additional_charge_amount'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['additional_charge_total'] / price_itinerary['additional_charge_amount'],
                    'pax_count': price_itinerary['additional_charge_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Additional Charge',
                })

            if price_itinerary.get('child_amount'):
                service_charge.append({
                    'pax_type': 'CHD',
                    'charge_code': 'fare',
                    'charge_type': 'fare',
                    'amount': price_itinerary['child_price'] / price_itinerary['child_amount'],
                    'pax_count': price_itinerary['child_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Child Price',
                })
                service_charge.append({
                    'pax_type': 'CHD',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['airport_tax_total'] / (price_itinerary['adult_amount'] + price_itinerary['child_amount'] + price_itinerary['infant_amount']),
                    'pax_count': price_itinerary['child_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Airport Tax',
                })

            if price_itinerary.get('child_surcharge_amount'):
                service_charge.append({
                    'pax_type': 'CHD',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['child_surcharge_price'] / price_itinerary['child_surcharge_amount'],
                    'pax_count': price_itinerary['child_surcharge_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Child Surcharge',
                })

            if price_itinerary.get('infant_amount'):
                service_charge.append({
                    'pax_type': 'INF',
                    'charge_code': 'fare',
                    'charge_type': 'fare',
                    'amount': price_itinerary['infant_price'] / price_itinerary['infant_amount'],
                    'pax_count': price_itinerary['infant_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Infant Price',
                })
                service_charge.append({
                    'pax_type': 'INF',
                    'charge_code': 'tax',
                    'charge_type': 'tax',
                    'amount': price_itinerary['airport_tax_total'] / (price_itinerary['adult_amount'] + price_itinerary['child_amount'] + price_itinerary['infant_amount']),
                    'pax_count': price_itinerary['infant_amount'],
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Airport Tax',
                })

            if price_itinerary.get('commission_total'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'r.ac',
                    'charge_type': 'r.ac',
                    'amount': price_itinerary['commission_total'] * -1,
                    'pax_count': 1,
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Commission',
                })

            if price_itinerary.get('commission_total'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'r.oc',
                    'charge_type': 'r.oc',
                    'amount': price_itinerary['commission_total'],
                    'pax_count': 1,
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Commission',
                })

            if price_itinerary.get('discount_total_itinerary_price'):
                service_charge.append({
                    'pax_type': 'ADT',
                    'charge_code': 'disc',
                    'charge_type': 'disc',
                    'amount': price_itinerary['discount_total_itinerary_price'] * -1,
                    'pax_count': 1,
                    'currency_id': def_currency,
                    'foreign_currency_id': def_currency,
                    'foreign_amount': 0,
                    'description': 'Discount',
                })

            for rec in service_charge:
                sc_obj = self.env['tt.service.charge'].create(rec)

                if sc_obj:
                    service_charge_ids.append(sc_obj.id)

            provider_id = self.env['tt.provider'].sudo().search([('code', '=', tour_data['provider'])])
            if provider_id:
                provider_id = provider_id[0]

            contact_data = self.env['tt.customer'].browse(int(contact_id))
            contact_phones = []
            for pho in contact_data.phone_ids:
                contact_phones.append(pho.phone_number)
            booking_obj = self.env['tt.reservation.tour'].sudo().create({
                'contact_id': contact_id,
                'contact_name': contact_data.name,
                'contact_email': contact_data.email,
                'contact_phone': contact_phones[0],
                'booker_id': booker_id,
                'passenger_ids': [(6, 0, pax_ids)],
                'agent_id': context['co_agent_id'],
                'user_id': context['co_uid'],
                'tour_id': pricelist_id,
                'transport_type': 'tour',
                'sale_service_charge_ids': [(6, 0, service_charge_ids)],
            })

            if booking_obj:
                booking_obj.action_booked_tour()
                provider_tour_vals = {
                    'booking_id': booking_obj.id,
                    'tour_id': pricelist_id,
                    'provider_id': provider_id.id,
                    'departure_date': tour_data['departure_date'],
                    'return_date': tour_data['return_date'],
                    # 'balance_due': req['amount'],
                }

                provider_tour_obj = self.env['tt.provider.activity'].sudo().create(provider_tour_vals)
                for psg in booking_obj.passenger_ids:
                    vals = {
                        'provider_id': provider_tour_obj.id,
                        'passenger_id': psg.id,
                        'pax_type': psg.pax_type,
                        'tour_room_id': psg.tour_room_id.id
                    }
                    self.env['tt.ticket.activity'].sudo().create(vals)
                provider_tour_obj.delete_service_charge()
                # for rec in pricing:
                #     provider_tour_obj.create_service_charge(rec)

                if force_issued == 1:
                    booking_obj.write({
                        'payment_method': data.get('payment_method') and data['payment_method'] or 'cash'
                    })
                    booking_obj.action_issued()

                response = {
                    'booking_num': booking_obj.name
                }

            else:
                response = {
                    'booking_num': 0
                }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def get_booking_api(self, data, context, **kwargs):
        try:
            search_booking_num = data.get('order_number')
            book_objs = self.env['tt.reservation.tour'].sudo().search([('name', '=', search_booking_num)])
            book_obj = book_objs[0]
            result = {
                'id': book_obj.id,
                'pnr': book_obj.pnr,
                'state': book_obj.state,
                'display_mobile': book_obj.display_mobile,
                'elder': book_obj.elder,
                'adult': book_obj.adult,
                'child': book_obj.child,
                'infant': book_obj.infant,
                'departure_date': book_obj.departure_date,
                'return_date': book_obj.return_date,
                'name': book_obj.name,
                'hold_date': book_obj.hold_date,
            }

            if book_obj.contact_id:
                contact_phone = self.env['phone.detail'].sudo().search([('customer_id', '=', book_obj.contact_id.id)])
                result.update({
                    'contact_first_name': book_obj.contact_id.first_name and book_obj.contact_id.first_name or '',
                    'contact_last_name': book_obj.contact_id.last_name and book_obj.contact_id.last_name or '',
                    'contact_title': book_obj.contact_id.title and book_obj.contact_id.title or '',
                    'contact_email': book_obj.contact_id.email and book_obj.contact_id.email or '',
                    'contact_phone': contact_phone[0].phone_number
                })

            tour_package = {
                'id': book_obj.tour_id.id,
                'name': book_obj.tour_id.name,
                'duration': book_obj.tour_id.duration,
                'departure_date': book_obj.tour_id.departure_date,
                'return_date': book_obj.tour_id.return_date,
                'departure_date_f': datetime.strptime(str(book_obj.tour_id.return_date), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                'return_date_f': datetime.strptime(str(book_obj.tour_id.return_date), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                'visa': book_obj.tour_id.visa,
                'flight': book_obj.tour_id.flight,
            }

            passengers = []
            rooms = []
            room_id_list = []
            for rec in book_obj.line_ids:
                passengers.append({
                    'pax_id': rec.passenger_id.id,
                    'first_name': rec.passenger_id.first_name and rec.passenger_id.first_name or '',
                    'last_name': rec.passenger_id.last_name and rec.passenger_id.last_name or '',
                    'title': rec.passenger_id.title and rec.passenger_id.title or '',
                    'pax_type': rec.pax_type,
                    'birth_date': rec.passenger_id.birth_date,
                    'room_id': rec.room_id.id,
                    'room_name': rec.room_id.name,
                    'room_bed_type': rec.room_id.bed_type,
                    'room_hotel': rec.room_id.hotel,
                    'room_number': rec.room_number,
                })

                if rec.room_id.id not in room_id_list:
                    room_id_list.append(rec.room_id.id)
                    rooms.append({
                        'room_number': rec.room_number,
                        'room_name': rec.room_id.name,
                        'room_bed_type': rec.room_id.bed_type,
                        'room_hotel': rec.room_id.hotel and rec.room_id.hotel or '-',
                        'room_notes': rec.description and rec.description or '-',
                    })

            price_itinerary = {
                'adult_amount': 0,
                'adult_price': 0,
                'adult_surcharge_amount': 0,
                'adult_surcharge_price': 0,
                'child_amount': 0,
                'child_price': 0,
                'child_surcharge_amount': 0,
                'child_surcharge_price': 0,
                'infant_amount': 0,
                'infant_price': 0,
                'single_supplement_amount': 0,
                'single_supplement_price': 0,
                'airport_tax_amount': 0,
                'airport_tax_total': 0,
                'tipping_guide_amount': 0,
                'tipping_guide_total': 0,
                'tipping_tour_leader_amount': 0,
                'tipping_tour_leader_total': 0,
                'additional_charge_amount': 0,
                'additional_charge_total': 0,
                'sub_total_itinerary_price': 0,
                'discount_total_itinerary_price': 0,
                'total_itinerary_price': 0,
                'commission_total': 0,
            }

            grand_total = 0
            for price in book_obj.sale_service_charge_ids:
                if price.description == 'Adult Price':
                    price_itinerary.update({
                        'adult_amount': price.pax_count,
                        'adult_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Airport Tax':
                    price_itinerary.update({
                        'airport_tax_amount': price.pax_count,
                        'airport_tax_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Adult Surcharge':
                    price_itinerary.update({
                        'adult_surcharge_amount': price.pax_count,
                        'adult_surcharge_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Single Supplement':
                    price_itinerary.update({
                        'single_supplement_amount': price.pax_count,
                        'single_supplement_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Tipping Tour Guide':
                    price_itinerary.update({
                        'tipping_guide_amount': price.pax_count,
                        'tipping_guide_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Tipping Tour Leader':
                    price_itinerary.update({
                        'tipping_tour_leader_amount': price.pax_count,
                        'tipping_tour_leader_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Additional Charge':
                    price_itinerary.update({
                        'additional_charge_amount': price.pax_count,
                        'additional_charge_total': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Child Price':
                    price_itinerary.update({
                        'child_amount': price.pax_count,
                        'child_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Child Surcharge':
                    price_itinerary.update({
                        'child_surcharge_amount': price.pax_count,
                        'child_surcharge_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Infant Price':
                    price_itinerary.update({
                        'infant_amount': price.pax_count,
                        'infant_price': int(price.total),
                    })
                    grand_total += int(price.total)
                if price.description == 'Commission' and price.charge_code == 'r.oc':
                    price_itinerary.update({
                        'commission_total': int(price.total),
                    })
                if price.description == 'Discount':
                    price_itinerary.update({
                        'discount_total_itinerary_price': int(price.total),
                    })
                    grand_total -= int(price.total)

            sub_total = grand_total + price_itinerary['discount_total_itinerary_price']

            price_itinerary.update({
                'total_itinerary_price': grand_total,
                'sub_total_itinerary_price': sub_total,
            })

            response = {
                'result': result,
                'tour_package': tour_package,
                'passengers': passengers,
                'rooms': rooms,
                'price_itinerary': price_itinerary,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def update_booking_api(self, data, context, **kwargs):
        try:
            search_booking_num = data.get('order_number')
            book_objs = self.env['tt.reservation.tour'].sudo().search([('name', '=', search_booking_num)])
            for book_obj in book_objs:
                book_obj.action_issued_tour()

            response = {
                'order_number': book_objs[0].name,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def update_passenger_api(self, data, context, **kwargs):
        try:
            booker_data = data['booking_data'].get('booker') and data['booking_data']['booker'] or False
            contacts_data = data['booking_data'].get('contact') and data['booking_data']['contact'] or False
            passengers = data['booking_data'].get('all_pax') and data['booking_data']['all_pax'] or False
            tour_data = data['booking_data'].get('tour_data') and data['booking_data']['tour_data'] or False
            res_pax_ids = []

            booker_obj = self.create_booker_api(booker_data, context)
            contact_data = contacts_data[0]
            contact_objs = []
            for con in contacts_data:
                contact_objs.append(self.create_contact_api(con, booker_obj, context))

            contact_obj = contact_objs[0]

            pax_ids = self.create_customer_api(passengers, context, booker_obj.seq_id, contact_obj.seq_id,
                                               ['title', 'pax_type', 'tour_room_id'])

            for idx, psg in enumerate(pax_ids):
                temp_obj = psg[0]
                extra_dict = psg[1]
                vals = temp_obj.copy_to_passenger()
                vals.update({
                    'title': extra_dict['title'],
                    'pax_type': extra_dict['pax_type'],
                    'tour_room_id': extra_dict.get('tour_room_id', 0),
                    'master_tour_id': tour_data and tour_data['id'] or False,
                    'sequence': idx + 1,
                })
                psg_obj = self.env['tt.reservation.passenger.tour'].sudo().create(vals)
                res_pax_ids.append(psg_obj.id)

            response = {
                'booker_id': booker_obj.id,
                'contact_id': contact_data.id,
                'pax_ids': res_pax_ids,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

