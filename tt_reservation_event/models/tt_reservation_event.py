from odoo import api, fields, models, _
from datetime import datetime, timedelta, date, time
from odoo import http
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.db_connector import GatewayConnector

try:
    from cStringIO import StringIO
except ImportError:
    pass

import pickle
import json
import base64
import logging
import traceback
import requests

# from Ap
_logger = logging.getLogger(__name__)


class EventResendVoucher(models.TransientModel):
    _name = "event.voucher.wizard"
    _description = 'Orbis Event Model'

    def get_default_email(self):
        context = self.env.context
        new_obj = self.env[context['active_model']].browse(context['active_id'])
        return new_obj.contact_id.email or False

    def get_default_provider(self):
        context = self.env.context
        new_obj = self.env[context['active_model']].browse(context['active_id'])
        return new_obj.provider_name

    def get_default_pnr(self):
        context = self.env.context
        new_obj = self.env[context['active_model']].browse(context['active_id'])
        return new_obj.pnr

    user_email_address = fields.Char(string="User Email", default=get_default_email)
    provider_name = fields.Char(string="Provider", default=get_default_provider, readonly=1)
    pnr = fields.Char(string="PNR", default=get_default_pnr)

    def resend_voucher_api(self):
        req = {
            'provider': self.provider_name,
            'order_id': self.pnr,
            'user_email_address': self.user_email_address
        }
        res = self.env['tt.event.api.con'].resend_voucher(req)
        if res['response'].get("success"):
            context = self.env.context
            new_obj = self.env[context['active_model']].browse(context['active_id'])
        else:
            raise UserError(_('Resend voucher failed!'))


class ReservationEvent(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.event'
    _order = 'id DESC'
    _description = 'Orbis Event Model'

    booking_uuid = fields.Char('Booking UUID')
    user_id = fields.Many2one('res.users', 'User')
    senior = fields.Integer('Senior')

    acceptance_date = fields.Datetime('Acceptance Date')
    rejected_date = fields.Datetime('Rejected Date')
    refund_date = fields.Datetime('Refund Date')

    event_id = fields.Many2one('tt.master.event', 'Event ID')
    event_name = fields.Char('Event Name')
    event_vendor_id = fields.Many2one('tt.vendor', 'Vendor')
    event_vendor = fields.Char('Event Vendor')
    event_product_uuid = fields.Char('Product Type UUID')
    # visit_date = fields.Datetime('Visit Date')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_event_id', string="Service Charge", readonly=True, states={'draft': [('readonly', False)]})
    provider_booking_ids = fields.One2many('tt.provider.event', 'booking_id', string="Provider Booking", readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.event', 'booking_id', string="Passengers")

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    information = fields.Text('Additional Information', help='Information from vendor to customer / agent')
    special_request = fields.Text('Special Request', help='Request / Notes from customer')
    file_upload = fields.Text('File Upload')
    voucher_url = fields.Text('Voucher URL')
    voucher_url_ids = fields.One2many('tt.reservation.event.voucher', 'booking_id')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_event.tt_provider_type_event'))
    option_ids = fields.One2many('tt.reservation.event.option', 'booking_id', 'Options')
    # extra_question_ids = fields.One2many('tt.reservation.event.extra.question', 'reservation_id', 'Extra Question')

    printout_vendor_invoice_id = fields.Many2one('tt.upload.center', 'Vendor Invoice', readonly=True)

    def get_form_id(self):
        return self.env.ref("tt_reservation_event.tt_reservation_event_form_view")

    @api.depends("passenger_ids.channel_service_charge_ids")
    def _compute_total_channel_upsell(self):
        for rec in self:
            chan_upsell_total = 0
            for pax in rec.passenger_ids:
                for csc in pax.channel_service_charge_ids:
                    chan_upsell_total += csc.amount
            rec.total_channel_upsell = chan_upsell_total

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

    def _calc_grand_total(self):
        for i in self:
            i.total = 0
            i.total_fare = 0
            i.total_tax = 0
            i.total_discount = 0
            i.total_commission = 0

            for j in i.sale_service_charge_ids:
                if j.charge_code == 'fare':
                    i.total_fare += j.total
                if j.charge_code == 'tax':
                    i.total_tax += j.total
                if j.charge_code == 'disc':
                    i.total_discount += j.total
                if j.charge_code == 'r.oc':
                    i.total_commission += j.total

            i.total = i.total_fare + i.total_tax
            i.total_nta = i.total - i.total_commission

    def action_booked(self, context):
        # Create Order Number
        order_number = self.env['ir.sequence'].next_by_code(self._name)
        self.name = order_number
        self.write({
            'state': 'booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now(),
        })

    def get_datetime(self, utc=0):
        now_datetime = datetime.now() + timedelta(hours=utc)
        if utc >= 0:
            utc = '+{}'.format(utc)
        return '{} (GMT{})'.format(now_datetime.strftime('%d-%b-%Y %H:%M:%S'), utc)

    def action_refund(self):
        self.write({
            'state': 'refund',
            'refund_date': datetime.now(),
            'refund_uid': self.env.user.id
        })

    def action_fail_refund(self, context):
        self.write({
            'state': 'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def action_partial_booked_api_event(self, context, pnr_list, hold_date):
        if type(hold_date) != datetime:
            hold_date = False
        self.write({
            'state': 'partial_booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now(),
            'hold_date': hold_date,
            'pnr': ','.join(pnr_list)
        })

    def action_partial_issued_api_event(self):
        self.write({
            'state': 'partial_issued'
        })

    def action_expired(self):
        self.write({
            'state': 'cancel2',
            'expired_date': datetime.now()
        })
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'

    def check_provider_state(self, context, pnr_list=[], hold_sate=False, req={}):
        if all(i.state == 'booked' for i in self.provider_booking_ids):
            #booked
            pass
        elif all(i.state == 'issued' for i in self.provider_booking_ids):
            #issued
            pass
        elif all(i.state == 'refund' for i in self.provider_booking_ids):
            #refund
            self.action_refund()
        elif all(i.state == 'fail_refunded' for i in self.provider_booking_ids):
            #fail_refunded, function ini setara dengan action_reverse_event
            self.action_fail_refund(context)
        elif any(i.state == 'issued' for i in self.provider_booking_ids):
            #partially issued
            self.action_partial_issued_api_event()
        elif any(i.state == 'booked' for i in self.provider_booking_ids):
            #partially_booked
            self.action_partial_booked_api_event()
        elif all(i.state == 'fail_issued' for i in self.provider_booking_ids):
            #failed issued
            self.action_failed_issue()
        elif all(i.state == 'fail_booked' for i in self.provider_booking_ids):
            #fail booked
            self.action_failed_book()
        else:
            _logger.error("Status unknown")
            raise RequestException(1006)

    def action_calc_prices(self):
        self._calc_grand_total()

    def action_adding_new_answer(self, data, context):
        reservation_id = data['reservation_id']
        for i in data['question_answer']:
            temp_dict = {
                'reservation_id': reservation_id,
                'extra_question_id': i['extra_question_id'],
                'answer': i['answer']
            }
            self.env['tt.reservation.event.extra.question'].create(temp_dict)

    def create_booking_event_api(self, req, context):
        def format_idx(idx):
            idx = str(idx)
            for a in range(3 - len(idx)):
                idx = '0' + idx
            return idx

        try:
            #retrieve and handling data
            booker_data = req.get('booker')
            contacts_data = req.get('contact')
            passengers = req.get('passengers')
            event_uuid = req.get('event_code')
            event_option_codes = req.get('event_option_codes')
            provider = req.get('provider')
            event_answer = req.get('event_answer', [])
            special_request = req.get('special_request', 'No Special Request')

            #create all dependencies
            booker_obj = self.create_booker_api(booker_data, context)
            contact_obj = self.create_contact_api(contacts_data[0], booker_obj, context)


            #get all necessary data
            provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
            event_id = self.env['tt.master.event'].sudo().search([('uuid', '=', event_uuid)], limit=1)

            #build temporary dict
            temp_main_dictionary = {
                'event_id': event_id.id,
                'event_name': event_id and event_id.name or req.get('event_name'),
                'event_vendor_id': event_id and event_id.event_vendor_id.id or False,
                'event_vendor': event_id and event_id.event_vendor_id.name or req.get('provider'),
                'event_product_uuid': event_id and event_id.uuid or req.get('event_code'),
                'provider_name': ','.join([provider_id.name,]),
                'booker_id': booker_obj.id,
                'contact_id': contact_obj.id,
                'contact_title': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': contact_obj.phone_ids and contact_obj.phone_ids[0].phone_number or False,
                'ho_id': context['co_ho_id'],
                'agent_id': context['co_agent_id'],
                'customer_parent_id': context.get('co_customer_parent_id', False),
                'user_id': context['co_uid'],
                'sid_booked': context['signature'],
                # 'passenger_ids': [6,0,[x.id for x in pax_ids]],
                'special_request': special_request,
            }
            book_obj = self.create(temp_main_dictionary)

            balance_due = 0
            # Create Provider Ids
            prov_event_id = self.env['tt.provider.event'].create({
                'provider_id': provider_id.id,
                'booking_id': book_obj.id,
                'balance_due': balance_due,  # di PNR
                'event_id': event_id and event_id.id or False,
            })
            #fill child table of resrevation event
            cust_id = self.create_customer_api(passengers, context, booker_obj.seq_id, contact_obj.seq_id)
            cust_id = cust_id[0]

            idx1 = 0
            for opt_obj in event_option_codes:
                for i in range(opt_obj['qty']):
                    idx1 += 1
                    event_option_id = self.env['tt.event.option'].sudo().search([('event_id', '=', event_id.id),('option_code', '=', opt_obj['option_code'])], limit=1)
                    temp_option_dict = {
                        'booking_id': book_obj.id,
                        'event_option_id': event_option_id and event_option_id.id or False,
                        'validator_sequence': opt_obj['option_code'] + format_idx(idx1)
                    }
                    option_obj = self.env['tt.reservation.event.option'].create(temp_option_dict)

                    for idx, j in enumerate(event_answer):
                        if opt_obj['option_code'] == j['option_code']:
                            for j1 in j['answer']:
                                temp_extra_question_dict = {
                                    'reservation_event_option_id': option_obj.id,
                                    # 'extra_question_id': j1['question_id'],
                                    'question': j1['que'],
                                    'answer': j1['ans'],
                                }
                                self.env['tt.reservation.event.extra.question'].create(temp_extra_question_dict)
                            event_answer.pop(idx)
                            break

                    pax_event_id = self.env['tt.reservation.passenger.event'].create({
                        'booking_id': book_obj.id,
                        'provider_id': prov_event_id.id,
                        'pax_type': 'ADT',
                        'option_id': option_obj.id,
                        'customer_id': cust_id.id,
                        'first_name': cust_id.first_name,
                        'last_name': cust_id.last_name,
                        'name': cust_id.name,
                        'birth_date': cust_id.birth_date,
                        'nationality_id': cust_id.nationality_id and cust_id.nationality_id.id or False,
                        # 'sequence': cust_id.sequence,
                        # 'title': cust_id.title,
                        # 'gender': cust_id.gender,
                        # 'identity_type': cust_id.identity_type,
                        # 'identity_number': cust_id.identity_number,
                        # 'identity_expdate': cust_id.identity_expdate,
                        # 'identity_country_of_issued_id': cust_id.identity_country_of_issued_id and cust_id.identity_country_of_issued_id.id or False,
                    })

                    for scs in opt_obj['service_charges']:
                        if scs['charge_type'] not in ['rac', 'roc']:
                            balance_due += scs['amount'] * scs['pax_count']

                            # Cost Service Charge
                            sc_id = self.env['tt.service.charge'].create({
                                'provider_event_booking_id': book_obj.provider_booking_ids[0].id,
                                'charge_code': scs['charge_code'],
                                'charge_type': scs['charge_type'],
                                'pax_type': scs['pax_type'],
                                'pax_count': scs['pax_count'],
                                'amount': scs['amount'],
                                'foreign_amount': scs['foreign_amount'],
                                'total': scs['amount'] * scs['pax_count'],
                                'description': book_obj.pnr and book_obj.pnr or '',
                                'commission_agent_id': scs['commission_agent_id'],
                            })
                            pax_event_id.update({'cost_service_charge_ids': [(4, sc_id.id)]})

                        # Sale Service Charge
                        self.env['tt.service.charge'].create({
                            'booking_event_id': book_obj.id,
                            # 'cost_service_charge_ids': [(4, pax_event_id.id)],
                            'charge_code': scs['charge_code'],
                            'charge_type': scs['charge_type'],
                            'pax_type': scs['pax_type'],
                            'pax_count': scs['pax_count'],
                            'amount': scs['amount'],
                            'foreign_amount': scs['foreign_amount'],
                            'total': scs['amount'] * scs['pax_count'],
                            'description': book_obj.pnr and book_obj.pnr or '',
                            'commission_agent_id': scs['commission_agent_id'],
                        })

            # Create Provider Ids
            prov_event_id['balance_due'] = balance_due  # di PNR
            book_obj.action_booked(context)

            ## 22 JUN 2023 - IVAN
            ## GET CURRENCY CODE
            currency = ''
            for provider_booking in book_obj.provider_booking_ids:
                for svc in provider_booking.cost_service_charge_ids:
                    currency = svc.currency_id.name
            if currency:
                currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
                if currency_obj:
                    book_obj.currency_id = currency_obj.id

            # channel repricing upsell
            if req.get('repricing_data'):
                req['repricing_data']['order_number'] = book_obj.name
                self.env['tt.reservation'].channel_pricing_api(req['repricing_data'], context)
                book_obj.create_svc_upsell()

            ## PAKAI VOUCHER
            if req.get('voucher'):
                book_obj.add_voucher(req['voucher']['voucher_reference'], context)

            response = {
                'book_id': book_obj.id,
                'order_number': book_obj.name,
                'option_ids': [rec.to_dict() for rec in book_obj.passenger_ids],
                'provider_ids': provider_id.id,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc() + '\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc() + '\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def set_pnr_booking_event_api(self, req, context):
        booking_obj = self.search([('name', '=', req['order_number'])], limit=1)
        if booking_obj:
            booking_obj.update({'pnr': req['pnr'], 'hold_date': req['hold_date']})
            for rec in req['providers']:
                for prov in booking_obj.provider_booking_ids.filtered(lambda x: x.provider_id.code == rec):
                    prov.update({
                        'pnr': req['pnr'],
                        'pnr2': req['pnr'],
                        'state': 'booked',
                        'hold_date': req['hold_date'],
                        'sid_booked': context['sid'],
                        'booked_uid': context['co_uid'],
                        'booked_date': datetime.now(),
                    })
            return ERR.get_no_error({
                'book_id': booking_obj.id,
                'order_number': booking_obj.name,
                'status': booking_obj.state,
                'hold_date': booking_obj.hold_date,
                'PNR': booking_obj.pnr,
            })
        else:
            return ERR.get_error(1004)

    # def to_dict(self):
    #     return {
    #         'order_number': self.name,
    #         'providers': [{'provider': rec.provider_id.code, 'pnr': self.pnr} for rec in self.provider_booking_ids],
    #         'event_name': self.event_name,
    #         'event_location': self.event_id and [{
    #             'name': rec.name,
    #             'address': rec.address,
    #             'city': rec.city_name,
    #             'country': rec.country_name,
    #             'lat': '',
    #             'long': '',
    #         } for rec in self.event_id.location_ids] or [],
    #         'hold_date': self.hold_date,
    #         'description': self.event_id and self.event_id.description or '',
    #         'options': [rec.to_dict() for rec in self.passenger_ids],
    #         'notes': '',
    #         'booker': self.booker_id.to_dict(),
    #         'contact': self.contact_id.to_dict(),
    #         'status': self.state,
    #     }

    def get_booking_from_backend(self, data, context):
        try:
            resv_obj = self.get_book_obj(data.get('order_id'), data.get('order_number'))
            try:
                resv_obj.create_date
            except:
                raise RequestException(1001)

            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                raise RequestException(1008)
            # if resv_obj.agent_id.id == context.get('co_agent_id',-1) or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids or resv_obj.agent_type_id.name == self.env.ref('tt_base.agent_b2c').agent_type_id.name or resv_obj.user_id.login == self.env.ref('tt_base.agent_b2c_user').login:
            # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
            _co_user = self.env['res.users'].sudo().browse(int(context['co_uid']))
            if resv_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_system'):
                res = resv_obj.to_dict(context)
                # res = resv_obj.to_dict()
                res.pop('departure_date')
                res.pop('arrival_date')
                res.pop('book_id')
                res.pop('agent_id')
                psg_list = []
                for i in resv_obj.passenger_ids:
                    if list(filter(lambda x: x['name'] == i.option_id.event_option_name, psg_list)):
                        list(filter(lambda x: x['name'] == i.option_id.event_option_name, psg_list))[0]['qty'] += 1
                    else:
                        new_i = i.to_dict()
                        new_i.update({
                            'name': i.option_id.event_option_name,
                            'qty': 1
                        })
                        psg_list.append(new_i)
                res.update({
                    'providers': [{'provider': rec.provider_id.code, 'pnr': rec.pnr} for rec in resv_obj.provider_booking_ids],
                    'event_name': resv_obj.event_name,
                    'event_location': resv_obj.event_id and [{
                        'name': rec.name,
                        'address': rec.address,
                        'city': rec.city_name,
                        'country': rec.country_name,
                        'lat': '',
                        'long': '',
                    } for rec in resv_obj.event_id.location_ids] or [],
                    'description': resv_obj.event_id and resv_obj.event_id.description or '',
                    'options': [rec.to_dict() for rec in resv_obj.passenger_ids],
                    'notes': '',
                    'passengers': psg_list
                })
                return ERR.get_no_error(res)
            else:
                raise RequestException(1003)

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()

    # def get_booking_from_backend(self, data, context):
    #     try:
    #         resv_obj = self.get_book_obj(data.get('order_id'), data.get('order_number'))
    #         if resv_obj:
    #             res = resv_obj.to_dict()
    #             # psg_list = []
    #             ticket_quantity = {}
    #             for i in resv_obj.passenger_ids:
    #                 if ticket_quantity.get(i.option_id.event_option_name):
    #                     ticket_quantity[str(i.option_id.event_option_name)].append(i.to_dict())
    #                 else:
    #                     ticket_quantity[i.option_id.event_option_name] = []
    #                     ticket_quantity[i.option_id.event_option_name].append(i.to_dict())
    #                 # psg_list.append(i.to_dict())
    #             res.update({
    #                 'passenger': ticket_quantity,
    #                 # 'ticket': ticket_quantity
    #             })
    #             return ERR.get_no_error(res)
    #         else:
    #             raise RequestException(1003)
    #
    #     except RequestException as e:
    #         _logger.error(traceback.format_exc())
    #         return e.error_dict()

    def payment_event_api(self, data, context):
        return self.payment_reservation_api('event', data, context)

    def action_issued_event(self, data):
        values = {
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': data.get('co_uid', self.env.user.id),
            'customer_parent_id': data['customer_parent_id']
        }
        self.write(values)

    def issued_booking_api(self, data, context):
        try:
            if data.get('order_id'):
                book_obj = self.env['tt.reservation.event'].sudo().browse(int(data['order_id']))
            else:
                book_objs = self.env['tt.reservation.event'].sudo().search([('name', '=', data['order_number'])],
                                                                          limit=1)
                book_obj = book_objs[0]

            acquirer_id, customer_parent_id = book_obj.get_acquirer_n_c_parent_id(data)

            req = {
                'co_uid': context['co_uid'],
                'customer_parent_id': customer_parent_id,
                'acquirer_id': acquirer_id,
                'payment_reference': data.get('payment_reference', ''),
                'payment_ref_attachment': data.get('payment_ref_attachment', []),
            }
            book_obj.action_issued_event(req)
            self.env.cr.commit()

            response = {
                'order_id': book_obj.id,
                'order_number': book_obj.name,
                'state': book_obj.state,
                'pnr': book_obj.pnr,
                'ADT': book_obj.adult,
                'CHD': book_obj.child,
                'INF': book_obj.infant,
                'YCD': book_obj.senior,
                'provider': [{
                    'provider': opt.event_option_id.event_id.provider_id.code or 'event_internal',
                    'booking_code': opt.event_option_id.event_id.provider_id.code,
                    'option': opt.event_option_id.option_code,
                } for opt in book_obj.option_ids],
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc() + '\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc() + '\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def set_provider_issued_event_api(self, req, context):
        booking_obj = self.search([('name', '=', req['order_number'])], limit=1)
        if booking_obj:
            for rec in req['providers']:
                for prov in booking_obj.provider_booking_ids.filtered(lambda x: x.provider_id.code == rec):
                    prov.update({
                        'pnr2': req['pnr'],
                        'state': 'issued',
                        'sid_issued': context['sid'],
                        'issued_uid': context['co_uid'],
                        'issued_date': datetime.now(),
                    })
            return ERR.get_no_error({
                'book_id': booking_obj.id,
                'order_number': booking_obj.name,
                'status': booking_obj.state,
                'hold_date': booking_obj.hold_date,
                'PNR': booking_obj.pnr,
            })

    def print_itinerary(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.event'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        event_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_event')
        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = event_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = event_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Event Itinerary %s.pdf' % book_obj.name,
                    'file_reference': 'Event Itinerary',
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
            'name': "Printout",
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

        book_obj = self.env['tt.reservation.event'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        event_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_event')
        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = event_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = event_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Event Itinerary %s (Price).pdf' % book_obj.name,
                    'file_reference': 'Event Itinerary',
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
            'name': "Printout",
            'target': 'new',
            'url': book_obj.printout_itinerary_price_id.url,
        }
        return url

    # DEPRECATED
    def print_ho_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        event_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_event')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = event_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = event_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Event HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Event HO Invoice',
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

    def print_vendor_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        event_vendor_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_vendor_event')
        if not self.printout_vendor_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = event_vendor_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = event_vendor_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Event Vendor Invoice %s.pdf' % self.name,
                    'file_reference': 'Event Vendor Invoice',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.sudo().printout_vendor_invoice_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_vendor_invoice_id.url,
        }
        return url
        # return event_vendor_invoice_id.report_action(self, data=datas)

    def print_eticket(self, data, ctx=None):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
            'is_hide_agent_logo': data.get('is_hide_agent_logo', False)
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        event_ticket_id = self.env.ref('tt_report_common.action_report_printout_reservation_event')
        if not self.printout_ticket_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = event_ticket_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = event_ticket_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Event Ticket %s.pdf' % self.name,
                    'file_reference': 'Event Ticket',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.sudo().printout_ticket_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_ticket_id.url,
            'path': self.printout_ticket_id.path
        }
        return url

    def print_eticket_with_price(self, data, ctx=None):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
            'is_hide_agent_logo': data.get('is_hide_agent_logo', False)
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        event_ticket_price_id = self.env.ref('tt_report_common.action_report_printout_reservation_event')
        if not self.printout_ticket_price_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = event_ticket_price_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = event_ticket_price_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Event Ticket (Price) %s.pdf' % self.name,
                    'file_reference': 'Event Ticket with Price',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.sudo().printout_ticket_price_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_ticket_price_id.url,
            'path': self.printout_ticket_price_id.path
        }
        return url

    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        # April 30, 2020 - SAM
        this_service_charges = []
        # END
        for idx, provider in enumerate(self.provider_booking_ids):
            sc_value = {}
            for idy, p_sc in enumerate(provider.cost_service_charge_ids):
                p_charge_code = p_sc.charge_code
                p_charge_type = p_sc.charge_type
                p_pax_type = p_sc.pax_type
                if not sc_value.get(p_pax_type):
                    sc_value[p_pax_type] = {}
                c_code = ''
                c_type = ''
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
                    'commission_agent_id': p_sc.commission_agent_id.id
                })

            # values = []
            for p_type,p_val in sc_value.items():
                for c_type,c_val in p_val.items():
                    # April 27, 2020 - SAM
                    curr_dict = {
                        'pax_type': p_type,
                        'booking_airline_id': self.id,
                        'description': provider.pnr,
                        'ho_id': self.ho_id.id if self.ho_id else ''
                    }
                    # curr_dict['pax_type'] = p_type
                    # curr_dict['booking_airline_id'] = self.id
                    # curr_dict['description'] = provider.pnr
                    # END
                    curr_dict.update(c_val)
                    # values.append((0,0,curr_dict))
                    # April 30, 2020 - SAM
                    this_service_charges.append((0,0,curr_dict))
                    # END
        # April 2020 - SAM
        #     self.write({
        #         'sale_service_charge_ids': values
        #     })
        self.write({
            'sale_service_charge_ids': this_service_charges
        })
        #END

    def get_passenger_pricing_breakdown(self):
        pax_list = []
        for rec in self.passenger_ids:
            pax_data = {
                'passenger_name': '%s %s' % (rec.title, rec.name),
                'pnr_list': []
            }
            for rec2 in self.provider_booking_ids:
                pax_ticketed = False
                ticket_num = ''
                for rec3 in rec2.ticket_ids.filtered(lambda x: x.passenger_id.id == rec.id):
                    pax_ticketed = True
                    if rec3.ticket_number:
                        ticket_num = rec3.ticket_number
                pax_pnr_data = {
                    'pnr': rec2.pnr,
                    'ticket_number': ticket_num,
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
                for rec3 in rec2.cost_service_charge_ids.filtered(lambda y: y.id in rec.cost_service_charge_ids.ids):
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


class TtReservationEventOption(models.Model):
    _name = 'tt.reservation.event.option'
    _description = 'Orbis Event Model'

    booking_id = fields.Many2one('tt.reservation.event', "Reservation ID")
    event_option_id = fields.Many2one('tt.event.option', 'Event Option')
    event_option_name = fields.Char('Option Name', related='event_option_id.grade', store=True)
    description = fields.Char('Description')
    extra_question_ids = fields.One2many('tt.reservation.event.extra.question', 'reservation_event_option_id', 'Extra Question')
    ticket_number = fields.Char('Ticket Number')
    ticket_file_ids = fields.Many2many('tt.upload.center', 'reservation_event_ticket_rel', 'reservation_event_id', 'ticket_id', 'Tickets')
    validator_sequence = fields.Char('Sequence')
    passenger_ids = fields.One2many('tt.reservation.passenger.event', 'option_id', 'Passengers')

    def to_dict(self):
        a = self.read(['ticket_number', 'validator_sequence'])
        a[0].update({
            'event_option_id': self.event_option_id.to_dict()[0],
            'extra_question': [rec.read(['question', 'answer'])[0] for rec in self.extra_question_ids]
        })
        return a[0]

class TtReservationEventVoucher(models.Model):
    _name = 'tt.reservation.event.voucher'
    _description = 'Orbis Event Model'

    name = fields.Char('URL')
    booking_id = fields.Many2one('tt.reservation.event', 'Reservation')


class TtReservationExtraQuestion(models.Model):
    _name = 'tt.reservation.event.extra.question'
    _description = 'Orbis Event Model'

    reservation_event_option_id = fields.Many2one('tt.reservation.event.option', 'Option')
    extra_question_id = fields.Many2one('tt.event.extra.question', 'Extra Question')
    question = fields.Char('Question')
    answer = fields.Char('answer')


class PrinoutEventInvoice(models.AbstractModel):
    _name = 'report.tt_reservation_event.printout_event_invoice'

    @api.model
    def render_html(self, docids, data=None):
        tt_event = self.env['tt.reservation.event'].browse(docids)
        docargs = {
            'doc_ids': docids,
            'doc': tt_event
        }
        return self.env['report'].with_context(landscape=False).render('tt_reservation_event.printout_event_invoice_template', docargs)
