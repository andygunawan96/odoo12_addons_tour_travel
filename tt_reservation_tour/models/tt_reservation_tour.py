from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
import logging
import traceback
import copy
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

# from Ap
_logger = logging.getLogger(__name__)

PAYMENT_METHOD = [
    ('cash', 'Cash'),
    ('installment', 'Installment')
]


class TourBooking(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.tour'

    tour_id = fields.Many2one('tt.reservation.tour.pricelist', 'Tour ID')
    # tour_id = fields.Char('Tour ID')

    line_ids = fields.One2many('tt.reservation.tour.line', 'tour_id', 'Line')  # Perlu tidak?

    arrival_date = fields.Date('Arrival Date', readonly=True, states={'draft': [('readonly', False)]})
    next_installment_date = fields.Date('Next Due Date', compute='_next_installment_date', store=True)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'tour_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    passenger_ids = fields.Many2many('tt.customer', 'tt_reservation_tour_passengers_rel', 'booking_id',
                                     'passenger_id',
                                     string='List of Passenger', readonly=True, states={'draft': [('readonly', False)]})
    # agent_invoice_ids = fields.One2many('tt.agent.invoice', 'res_id', 'Agent Invoice')  # One2Many -> tt.agent.invoice

    # provider_booking_ids = fields.One2many('tt.provider', 'booking_id', 'Provider Booking IDs')

    payment_method = fields.Selection(PAYMENT_METHOD, 'Payment Method')

    # *STATE*
    def action_booked(self):
        self.write({
            'state': 'booked',
            'booked_date': datetime.now(),
            'booked_uid': self.env.user.id,
            'hold_date': datetime.now() + relativedelta(days=1),
        })
        # self.message_post(body='Order BOOKED')

    def action_issued(self):
        self.write({
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': self.env.user.id
        })
        # self.message_post(body='Order ISSUED')

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

    param_contact_data = {
        'first_name': 'Ivan',
        'last_name': 'Suryajaya',
        'home_phone': '6231-5606500',
        'nationality_code': 'ID',
        'title': 'MR',
        'work_phone': '6231-5606500',
        'gender': 'male',
        'company_city_1': 'SURABAYA',
        'company_phone_2': '62315662000',
        'contact_id': False,
        'company_phone_1': '62315662000',
        'company_email_2': 'rodexbooking@gmail.com',
        'mobile': '08217317232',
        'company_email_1': 'booking@rodextravel.tours',
        'company_postal_code': '60241',
        'country_code': 'ID',
        'company_country_1': 'ID',
        'company_state_1': 'JTM',
        'other_phone': '',
        'email': 'Asndk@gmail.com',
        'company_address_1': 'JL. RAYA DARMO 177B'
    }

    param_passengers = {

    }

    param_service_charge_summary = {

    }

    param_tour_data = {

    }

    param_search_request = {

    }

    param_context = {

    }

    param_kwargs = {

    }

    # def test_booking(self):
    # self.create_booking(self.contact_data, self.passenger_data, self.option, self.search_request, '', self.context, self.kwargs)

    def create_booking(self):
        contact_data = copy.deepcopy(self.param_contact_data)
        passengers = copy.deepcopy(self.param_passengers)
        service_charge_summary = copy.deepcopy(self.param_service_charge_summary)
        tour_data = copy.deepcopy(self.param_tour_data)
        search_request = copy.deepcopy(self.param_search_request)
        context = copy.deepcopy(self.param_context)
        kwargs = copy.deepcopy(self.param_kwargs)

        try:
            self._validate_tour(context, 'context')
            self._validate_tour(search_request, 'header')
            context = self.update_api_context(int(contact_data.get('agent_id')), context)

            # ========= Validasi agent_id ===========
            # TODO : Security Issue VERY HIGH LEVEL
            # 1. Jika BUKAN is_company_website, maka contact.contact_id DIABAIKAN
            # 2. Jika ADA contact.contact_id MAKA agent_id = contact.contact_id.agent_id
            # 3. Jika TIDAK ADA contact.contact_id MAKA agent_id = co_uid.agent_id

            # PRODUCTION
            # # self.validate_booking(api_context=context)
            # user_obj = self.env['res.users'].sudo().browse(int(context['co_uid']))
            # contact_data.update({
            #     'agent_id': user_obj.agent_id.id,
            #     'commercial_agent_id': user_obj.agent_id.id,
            #     'booker_type': 'FPO',
            #     'display_mobile': user_obj.mobile,
            # })
            # if user_obj.agent_id.agent_type_id.id in (
            #         self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
            #     if user_obj.agent_id.parent_agent_id:
            #         contact_data.update({
            #             'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
            #             'booker_type': 'COR/POR',
            #             'display_mobile': user_obj.mobile,
            #         })
            #
            # # header_val = self._prepare_booking(journeys_booking, tour_data, search_request, context, kwargs)
            # header_val = self._tour_header_normalization(search_request)
            # contact_obj = self._create_contact(contact_data, context)
            #
            # psg_ids = self._evaluate_passenger_info(passengers, contact_obj.id, context['agent_id'])
            #
            # header_val.update({
            #     'contact_id': contact_obj.id,
            #     'state': 'booked',
            #     'agent_id': context['agent_id'],
            #     'user_id': context['co_uid'],
            #     'tour_id': tour_data['id'],
            #     'departure_date': search_request['tour_departure_date'],
            #     'arrival_date': search_request['tour_arrival_date'],
            # })
            #
            # # create header & Update SUB_AGENT_ID
            # book_obj = self.sudo().create(header_val)
            #
            # for psg in passengers:
            #     # if psg['room_number'].is_integer():
            #     is_int = isinstance(psg['room_number'], int)
            #     if is_int:
            #         room_number = psg['room_number'] + 1
            #         room_index = psg['room_number']
            #     else:
            #         room_number = int(psg['room_number'][5:])
            #         room_index = room_number - 1
            #     vals = {
            #         'tour_booking_id': book_obj.id,
            #         'passenger_id': psg['passenger_id'],
            #         'pax_type': psg['pax_type'],
            #         'pax_mobile': psg.get('mobile'),
            #         'room_number': 'Room ' + str(room_number),
            #         'extra_bed_description': context['room_data'][room_index]['description'],
            #         'room_id': psg['room_id'],
            #         'description': context['room_data'][room_index]['notes'],
            #         'pricelist_id': book_obj.tour_id.id
            #     }
            #     self.env['tt.reservation.tour.line'].sudo().create(vals)
            #
            # for rec in service_charge_summary:
            #     rec.update({
            #         'tour_booking_id': book_obj.id,
            #     })
            #     self.env['tt.reservation.tour.price'].sudo().create(rec)
            # self._calc_grand_total()
            #
            # book_obj.sub_agent_id = contact_data['agent_id']
            #
            # book_obj.action_booked_tour(context)
            # context['order_id'] = book_obj.id
            # if kwargs.get('force_issued'):
            #     book_obj.action_issued_tour(service_charge_summary, tour_data, kwargs, context)
            #     book_obj.calc_next_installment_date()
            #
            # # self._create_passengers(passengers, book_obj, contact_obj.id, context)
            #
            # self.env.cr.commit()
            # return {
            #     'error_code': 0,
            #     'error_msg': 'Success',
            #     'response': {
            #         'order_id': book_obj.id,
            #         'order_number': book_obj.name,
            #         'status': book_obj.state,
            #     }
            # }
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e)
            }

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

    def update_api_context(self, sub_agent_id, context):
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
                    'sub_agent_id': user_obj.agent_id.id,
                    'booker_type': 'COR/POR',
                })
            elif sub_agent_id:
                # ===== COR/POR in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'sub_agent_id': sub_agent_id,
                    'booker_type': 'COR/POR',
                })
            else:
                # ===== FPO in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'sub_agent_id': user_obj.agent_id.id,
                    'booker_type': 'FPO',
                })
        else:
            # ===============================================
            # ====== Context dari API Client ( BTBO ) =======
            # ===============================================
            context.update({
                'agent_id': user_obj.agent_id.id,
                'sub_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
            })
        return context
