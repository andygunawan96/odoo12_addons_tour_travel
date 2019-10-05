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


class TourBooking(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.tour'
    _description = 'Rodex Model'

    tour_id = fields.Many2one('tt.master.tour', 'Tour ID')
    # tour_id = fields.Char('Tour ID')

    line_ids = fields.One2many('tt.reservation.tour.line', 'tour_id', 'Line')  # Perlu tidak?

    next_installment_date = fields.Date('Next Due Date', compute='_next_installment_date', store=True)

    arrival_date = fields.Date('Arrival Date')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_tour_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})
    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger',
                                 domain=[('res_model', '=', 'tt.reservation.tour')])
    provider_booking_ids = fields.One2many('tt.provider.tour', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.tour', 'booking_id', string='Passengers')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_tour.tt_provider_type_tour'))
    payment_method = fields.Selection(PAYMENT_METHOD, 'Payment Method')

    # *STATE*
    def action_confirm(self):
        if self.state != 'confirm':
            self.write({
                'state': 'confirm',
                'name': self.env['ir.sequence'].next_by_code('reservation.tour.booking.code'),
            })

    def action_booked(self):
        if self.state != 'booked':
            self.write({
                'state': 'booked',
                'booked_date': datetime.now(),
                'booked_uid': self.env.user.id,
                'hold_date': datetime.now() + relativedelta(days=1),
            })
        # self.message_post(body='Order BOOKED')

    def action_issued(self):
        if self.state != 'issued':
            self.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': self.env.user.id
            })
            self.create_ledger_tour()
            self.create_commission_ledger_tour()

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
        # if not api_context:
        #     api_context = {
        #         'co_uid': self.env.user.id
        #     }
        # vals = {}
        # if self.name == 'New':
        #     vals.update({
        #         'name': self.env['ir.sequence'].next_by_code('transport.booking.tour'),
        #         'state': 'partial_booked',
        #     })
        self.action_booked()

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
            pax_ids_str = data.get('pax_ids') and data['pax_ids'] or '|'
            book_line_ids_str = data.get('book_line_ids') and data['book_line_ids'] or '|'
            temp = pax_ids_str.split('|')
            temp2 = book_line_ids_str.split('|')
            pax_ids = []
            book_line_ids = []
            service_charge = []
            service_charge_ids = []
            def_currency = self.env['res.currency'].search([('name', '=', 'IDR')])[0].id

            for rec in temp:
                if rec:
                    pax_ids.append(int(rec))

            for rec in temp2:
                if rec:
                    book_line_ids.append(int(rec))

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

            booking_obj = self.env['tt.reservation.tour'].sudo().create({
                'contact_id': booker_id != 'false' and int(booker_id) or False,
                'passenger_ids': [(6, 0, pax_ids)],
                'tour_id': pricelist_id,
                'agent_id': 2,
                'line_ids': [(6, 0, book_line_ids)],
                'sale_service_charge_ids': [(6, 0, service_charge_ids)],
            })

            if booking_obj:
                booking_obj.action_confirm()
                booking_obj.action_booked_tour()

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
                'arrival_date': book_obj.arrival_date,
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
                'arrival_date': book_obj.tour_id.arrival_date,
                'departure_date_f': datetime.strptime(str(book_obj.tour_id.arrival_date), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
                'arrival_date_f': datetime.strptime(str(book_obj.tour_id.arrival_date), '%Y-%m-%d').strftime("%A, %d-%m-%Y") or '',
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

    def issued_by_api(self, data, context, **kwargs):
        try:
            search_booking_num = data.get('order_number')
            book_objs = self.env['tt.reservation.tour'].sudo().search([('name', '=', search_booking_num)])
            for book_obj in book_objs:
                book_obj.action_issued()

            response = {
                'order_number': book_objs[0].name,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def update_passenger_api(self, data, context, **kwargs):
        try:
            sameBooker = False
            if data['booking_data']['sameBooker'] == "yes":
                sameBooker = True
            else:
                sameBooker = False

            booker_obj = data['booking_data']['booker']
            booker_id = booker_obj.get('booker_id')
            res_booker_id = False
            res_pax_list = []
            book_line_list = []
            contact_person = data['booking_data']['contact']
            tour_data = data['booking_data']['tour_data']
            if len(contact_person) > 0:
                similar = self.check_pax_similarity(contact_person[0])
                if not similar:
                    cust_obj = self.env['tt.customer'].sudo().create({
                        'title': contact_person[0].get('title'),
                        'first_name': contact_person[0].get('first_name'),
                        'last_name': contact_person[0].get('last_name'),
                        'email': contact_person[0].get('email'),
                        'agent_id': contact_person[0].get('agent_id') and contact_person[0]['agent_id'] or 2,
                    })
                    if contact_person[0].get('mobile'):
                        self.env['phone.detail'].sudo().create({
                            'customer_id': cust_obj.id,
                            'type': 'work',
                            'name': 'Work',
                            'phone_number': contact_person[0]['mobile'],
                        })
                    res_booker_id = cust_obj.id
                else:
                    res_booker_id = similar.id
            elif not sameBooker and not booker_id:
                similar = self.check_pax_similarity(booker_obj)
                if not similar:
                    cust_obj = self.env['tt.customer'].sudo().create({
                        'title': booker_obj.get('title'),
                        'first_name': booker_obj.get('first_name'),
                        'last_name': booker_obj.get('last_name'),
                        'email': booker_obj.get('email'),
                        'agent_id': booker_obj.get('agent_id') and booker_obj['agent_id'] or 2,
                    })
                    if booker_obj.get('mobile'):
                        self.env['phone.detail'].sudo().create({
                            'customer_id': cust_obj.id,
                            'type': 'work',
                            'name': 'Work',
                            'phone_number': booker_obj['mobile'],
                        })
                    res_booker_id = cust_obj.id
                else:
                    res_booker_id = similar.id

            elif booker_id and not sameBooker:
                temp_booker = self.env['tt.customer'].browse(int(booker_id))
                temp_booker.sudo().update({
                    'title': booker_obj.get('title') and booker_obj['title'] or temp_booker.title,
                    'first_name': booker_obj.get('first_name') and booker_obj['first_name'] or temp_booker.first_name,
                    'last_name': booker_obj.get('last_name') and booker_obj['last_name'] or temp_booker.last_name,
                    'email': booker_obj.get('email') and booker_obj['email'] or temp_booker.email,
                    'agent_id': booker_obj.get('agent_id') and booker_obj['agent_id'] or temp_booker.agent_id,
                })
                if booker_obj.get('mobile'):
                    found = False
                    for ph in temp_booker.phone_ids:
                        if ph.phone_number == booker_obj['mobile']:
                            found = True
                    if not found:
                        self.env['phone.detail'].sudo().create({
                            'customer_id': int(booker_id),
                            'type': 'work',
                            'name': 'Work',
                            'phone_number': booker_obj['mobile'],
                        })
                res_booker_id = int(booker_id)

            temp_idx = 0
            for rec in data['booking_data']['all_pax']:
                if not rec.get('passenger_id'):
                    similar = self.check_pax_similarity(rec)
                    if not similar:
                        cust_obj = self.env['tt.customer'].sudo().create({
                            'title': rec.get('title'),
                            'first_name': rec.get('first_name'),
                            'last_name': rec.get('last_name'),
                            'email': rec.get('email'),
                            'agent_id': rec.get('agent_id') and rec['agent_id'] or 2,
                            'birth_date': rec.get('birth_date_f'),
                            'passport_number': rec.get('passport_number'),
                            'passport_exp_date': rec.get('passport_expdate_f'),
                        })
                        if rec.get('mobile'):
                            self.env['phone.detail'].sudo().create({
                                'customer_id': cust_obj.id,
                                'type': 'work',
                                'name': 'Work',
                                'phone_number': rec['mobile'],
                            })
                        res_pax_list.append(cust_obj.id)
                        if sameBooker and temp_idx == 0 and rec.get('pax_type') == 'ADT':
                            cust_obj.update({
                                'email': booker_obj.get('email'),
                            })
                            if booker_obj.get('mobile'):
                                self.env['phone.detail'].sudo().create({
                                    'customer_id': cust_obj.id,
                                    'type': 'work',
                                    'name': 'Work',
                                    'phone_number': booker_obj['mobile'],
                                })
                            res_booker_id = cust_obj.id
                            temp_idx += 1

                        cust_line_obj = self.env['tt.reservation.tour.line'].sudo().create({
                            'passenger_id': cust_obj.id,
                            'room_id': rec.get('room_id') and rec['room_id'] or False,
                            'room_number': rec.get('room_seq') and rec['room_seq'] or False,
                            'pax_type': rec.get('pax_type') and rec['pax_type'] or False,
                            'tour_pricelist_id': tour_data and tour_data['id'] or False,
                        })
                        book_line_list.append(cust_line_obj.id)
                    else:
                        cust_line_obj = self.env['tt.reservation.tour.line'].sudo().create({
                            'passenger_id': similar.id,
                            'room_id': rec.get('room_id') and rec['room_id'] or False,
                            'room_number': rec.get('room_seq') and rec['room_seq'] or False,
                            'pax_type': rec.get('pax_type') and rec['pax_type'] or False,
                            'tour_pricelist_id': tour_data and tour_data['id'] or False,
                        })
                        book_line_list.append(cust_line_obj.id)

                else:
                    temp = self.env['tt.customer'].browse(int(rec['passenger_id']))
                    temp.sudo().update({
                        'title': rec.get('title') and rec['title'] or temp.title,
                        'first_name': rec.get('first_name') and rec['first_name'] or temp.first_name,
                        'last_name': rec.get('last_name') and rec['last_name'] or temp.last_name,
                        'email': rec.get('email') and rec['email'] or temp.email,
                        'agent_id': rec.get('agent_id') and rec['agent_id'] or temp.agent_id,
                        'birth_date': rec.get('birth_date_f') and rec['birth_date_f'] or temp.birth_date,
                        'passport_number': rec.get('passport_number') and rec['passport_number'] or temp.passport_number,
                        'passport_exp_date': rec.get('passport_expdate_f') and rec['passport_expdate_f'] or temp.passport_exp_date,
                    })
                    if rec.get('mobile'):
                        found = False
                        for ph in temp.phone_ids:
                            if ph.phone_number == rec['mobile']:
                                found = True
                        if not found:
                            self.env['phone.detail'].sudo().create({
                                'customer_id': int(rec['passenger_id']),
                                'type': 'work',
                                'name': 'Work',
                                'phone_number': rec['mobile'],
                            })
                    res_pax_list.append(int(rec['passenger_id']))
                    cust_line_obj = self.env['tt.reservation.tour.line'].sudo().create({
                        'passenger_id': int(rec['passenger_id']),
                        'room_id': rec.get('room_id') and rec['room_id'] or False,
                        'room_number': rec.get('room_seq') and rec['room_seq'] or False,
                        'pax_type': rec.get('pax_type') and rec['pax_type'] or False,
                        'tour_pricelist_id': tour_data and tour_data['id'] or False,
                    })
                    book_line_list.append(cust_line_obj.id)

            response = {
                'booker_data': res_booker_id,
                'pax_list': res_pax_list,
                'book_line': book_line_list,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

