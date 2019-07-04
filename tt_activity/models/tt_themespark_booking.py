from odoo import api, fields, models, _
from datetime import datetime, timedelta, date, time
from odoo import http

import pickle
import json
import base64
import logging
import traceback
import requests

_logger = logging.getLogger(__name__)


class ThemesparkBooking(models.Model):
    _name = 'tt.themespark.booking'
    _order = 'id DESC'
    _inherit = ['mail.thread']

    name = fields.Char('Name', required=True, default='New')
    sid = fields.Char('SID', readonly=True)
    pnr = fields.Char('PNR')
    booking_uuid = fields.Char('Booking UUID')

    date = fields.Datetime('Booked Date')
    booked_uid = fields.Many2one('res.users', 'Booked By')
    issued_date = fields.Datetime('Issued Date')
    issued_uid = fields.Many2one('res.users', 'Issued By', readonly=1)
    hold_date = fields.Datetime('Hold Date')

    user_id = fields.Many2one('res.users', 'User')
    senior = fields.Integer('Senior')
    adult = fields.Integer('Adult')
    child = fields.Integer('Child')
    infant = fields.Integer('Infant')

    acceptance_date = fields.Datetime('Acceptance Date')
    rejected_date = fields.Datetime('Rejected Date')
    expired_date = fields.Datetime('Expired Date')
    refund_date = fields.Datetime('Refund Date')

    themespark_id = fields.Many2one('tt.master.themespark', 'Activity')
    themespark_name = fields.Char('Activity Name')
    themespark_product = fields.Char('Product Type')
    themespark_product_uuid = fields.Char('Product Type Uuid')
    visit_date = fields.Datetime('Visit Date')
    agent_id = fields.Many2one('tt.agent', 'Agent')

    total = fields.Monetary('Grand Total', compute='_calc_grand_total', store=True)
    total_fare = fields.Monetary('Total Fare', compute='_calc_grand_total', store=True)
    total_tax = fields.Monetary('Total Tax', compute='_calc_grand_total', store=True)
    total_disc = fields.Monetary('Total Discount', compute='_calc_grand_total', store=True)
    sum_comisi = fields.Monetary('Total Commission', compute='_calc_grand_total', store=True)
    nta_amount = fields.Monetary('NTA Amount', compute='_calc_grand_total', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)

    information = fields.Text('Additional Information')
    vendor_ledger_id = fields.Many2one('tt.vendor.ledger', 'Provider Ledger')
    file_upload = fields.Text('File Upload')

    state = fields.Selection(
        [('reserved', 'Booked'), ('waiting', 'Issued'), ('approved', 'Approved'), ('rejected', 'Rejected'),
         ('done', 'Done'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('expired', 'Expired'),
         ('refunded', 'Refunded')],
        help='''booked/reserved = hold booking/reserved
                issued/waiting = issued/waiting for vendor confirmation
                expired = still on waiting state after 5days
                failed = failed booked/issued
                approved = approved by vendor
                rejected = rejected by vendor
                cancelled = cancelled by pax
                refunded = refund accepted after approved state
                done = done/after get voucher''')

    def _calc_grand_total(self):
        for rec in self:
            rec.total = 0
            rec.total_fare = 0
            rec.total_tax = 0
            rec.total_disc = 0
            rec.sum_comisi = 0

            for line in rec.sale_service_charge_ids:
                if line.charge_code == 'fare':
                    rec.total_fare += line.total
                if line.charge_code == 'tax':
                    rec.total_tax += line.total
                if line.charge_code == 'disc':
                    rec.total_disc += line.total
                if line.charge_code == 'r.oc':
                    rec.sum_comisi += line.total

            rec.total = rec.total_fare + rec.total_tax + rec.total_disc
            rec.nta_amount = rec.total - rec.sum_comisi

    @api.model
    def create(self, value):
        new = super(ThemesparkBooking, self.with_context(mail_create_nolog=True)).create(value)
        new.message_post(body='Order CREATED')
        return new

    # Start : Fungsi untuk Mengubah State
    def action_booked(self):
        self.write({
            'state': 'reserved',
            'date': datetime.now(),
            'booked_uid': self.env.user.id,
            # 'hold_date': datetime.now() + relativedelta(days=1),
        })
        self.message_post(body='Order BOOKED')

    def action_reserved(self):
        self.write({
            'state': 'reserved',
            'date': datetime.now(),
            'booked_uid': self.env.user.id,
            # 'hold_date': datetime.now() + relativedelta(days=1),
        })
        self.message_post(body='Order BOOKED')

    def action_waiting(self):
        self.write({
            'state': 'waiting',
            'issued_date': datetime.now(),
            'issued_uid': self.env.user.id,
        })
        self.message_post(body='Order ISSUED')

    def action_calc_prices(self):
        self._calc_grand_total()

    def action_confirm(self, commission, parent_commission, ho_commission):
        self.create_agent_invoice_themespark()
        self._create_ledger_themespark()
        self._create_commission_ledger_themespark(commission, parent_commission, ho_commission)
        self.message_post(body='Order ISSUED')

    def action_approved(self):
        self.write({
            'state': 'approved',
            'acceptance_date': datetime.now(),
        })
        self.message_post(body='Order APPROVED')

    def action_rejected(self):
        self.write({
            'state': 'rejected',
            'rejected_date': datetime.now(),
        })
        self.message_post(body='Order REJECTED')

    def action_expired(self):
        self.write({
            'state': 'expired',
            'expired_date': datetime.now(),
        })
        self.message_post(body='Order EXPIRED')

    def action_refunded(self):
        self.write({
            'state': 'refunded',
            'refund_date': datetime.now(),
        })

        # todo create refund ledger
        # self._create_refund_ledger_themespark()

        self.message_post(body='Order REFUNDED')

    def action_cancelled(self):
        for rec in self.invoice_id:
            rec.action_cancel()
        self._create_anti_ledger_themespark()
        self._create_anti_commission_ledger_themespark()
        self.write({
            'state': 'cancelled',
            'cancelled_date': datetime.now(),
            'cancelled_uid': self.env.user.id
        })
        self.message_post(body='Order CANCELLED')

    def action_failed(self, booking_id, error_msg):
        booking_rec = self.browse(booking_id)
        booking_rec.write({
            'state': 'failed',
            'error_msg': error_msg
        })
        return {
            'error_code': 0,
            'error_msg': False,
            'response': 'action_fail_booking'
        }

    def action_failed_sync(self):
        self.write({
            'state': 'failed',
        })
        self.message_post(body='Order FAILED')

    def action_done(self):
        self.write({
            'state': 'done',
        })
        self.message_post(body='Order DONE')
    # End

    def get_datetime(self, utc=0):
        now_datetime = datetime.now() + timedelta(hours=utc)
        # adjustment server time
        # now_datetime = adjustment_datetime(now_datetime, 0, 7, 6)
        if utc >= 0:
            utc = '+{}'.format(utc)
        return '{} (GMT{})'.format(now_datetime.strftime('%d-%b-%Y %H:%M:%S'), utc)

    def delete_prices(self, booking_id):
        try:
            booking_obj = self.browse(booking_id)  # get object booking
            for rec in booking_obj.ledger_id:  # looping through ledger_id
                if rec.transaction_type == 3:
                    ledger_type = 'commission'
                if rec.transaction_type == 23:
                    ledger_type = 'activity'
                vals = self.env['tt.ledger'].prepare_vals(rec.name, rec.ref, str(fields.Datetime.now()),
                                                          ledger_type, rec.currency_id.id, rec.credit, rec.debit)
                vals.update({
                    'agent_id': rec.agent_id.id,
                    'themespark_booking_id': booking_obj.id,
                })
                ledger_obj = self.env['tt.ledger'].create(vals)
                ledger_obj.action_done()
            for rec in booking_obj.invoice_id:
                rec.sudo().action_cancel()
            return {
                'error_code': 0,
                'error_msg': 'Success',
            }
        except Exception as e:
            return {
                'error_code': 1,
                'error_msg': str(e) + '\nDelete prices failure'
            }

    def _validate_themespark(self, data, type):
        list_data = []
        if type == 'context':
            list_data = ['co_uid', 'is_company_website']
        elif type == 'header':
            list_data = ['senior', 'adult', 'child', 'infant']

        keys_data = []
        for rec in data.iterkeys():
            keys_data.append(str(rec))

        for ls in list_data:
            if not ls in keys_data:
                raise Exception('ERROR Validate %s, key : %s' % (type, ls))
        return True

    def _themespark_header_normalization(self, data):
        res = {}
        int_key_att = ['senior', 'adult', 'child', 'infant']

        for rec in int_key_att:
            res.update({
                rec: int(data[rec])
            })

        return res

    def update_api_context(self, sub_agent_id, context):
        context['co_uid'] = int(context['co_uid'])
        user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
        if context['is_company_website']:
            #============================================
            #====== Context dari WEBSITE/FRONTEND =======
            #============================================
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

    def _create_contact(self, vals, context):
        country_obj = self.env['res.country'].sudo()
        contact_obj = self.env['tt.customer.details'].sudo()
        if vals.get('contact_id'):
            vals['contact_id'] = int(vals['contact_id'])
            contact_rec = contact_obj.browse(vals['contact_id'])
            if contact_rec:
                contact_rec.update({
                    'email': vals.get('email', contact_rec.email),
                    'mobile': vals.get('mobile', contact_rec.mobile),
                })
            return contact_rec

        country = country_obj.search([('code', '=', vals.pop('nationality_code'))])
        vals['nationality_id'] = country and country[0].id or False

        if context['booker_type'] == 'COR/POR':
            vals['passenger_on_partner_ids'] = [(4, context['sub_agent_id'])]

        country = country_obj.search([('code', '=', vals.pop('country_code'))])
        vals.update({
            'commercial_agent_id': context['agent_id'],
            'agent_id': context['agent_id'],
            'country_id': country and country[0].id or False,
            'pax_type': 'ADT',
            'bill_to': '<span><b>{title} {first_name} {last_name}</b> <br>Phone: {mobile}</span>'.format(**vals),
            'mobile_orig': vals.get('mobile', ''),
            'email': vals.get('email', vals['email']),
            'mobile': vals.get('mobile', vals['mobile']),
        })
        return contact_obj.sudo().create(vals)

    def _create_passengers(self, passengers, contact_obj, context):
        country_obj = self.env['res.country'].sudo()
        passenger_obj = self.env['tt.customer.details'].sudo()
        res_ids = []
        for psg in passengers:
            if psg.get('nationality_code'):
                country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
                psg['nationality_id'] = country and country[0].id or False
            if psg.get('country_of_issued_code'):
                country = country_obj.search([('code', '=', psg.pop('country_of_issued_code'))])
                psg['country_of_issued_id'] = country and country[0].id or False

            vals_for_update = {
                # 'passport_number': psg.get('passport_number'),
                # 'passport_expdate': psg.get('passport_expdate'),
                'nationality_id': psg['nationality_id'],
                # 'country_of_issued_id': psg.get('country_of_issued_id'),
                # 'passport_issued_date': psg.get('passport_issued_date'),
                # 'identity_type': psg.get('identity_type'),
                # 'identity_number': psg.get('identity_number'),
                'birth_date': psg.get('birth_date'),
                'email': psg.get('email'),
                'commercial_agent_id': contact_obj.commercial_agent_id.id,
                'agent_id': contact_obj.agent_id.id,
                'mobile': psg.get('mobile'),
            }

            psg_exist = False
            if psg['passenger_id']:
                psg['passenger_id'] = int(psg['passenger_id'])
                passenger_obj = self.env['tt.customer.details'].sudo().browse(psg['passenger_id'])
                if passenger_obj:
                    psg_exist = True
                    if context['booker_type'] == 'COR/POR':
                        vals_for_update['passenger_on_partner_ids'] = [(4, context['sub_agent_id'])]
                    passenger_obj.write(vals_for_update)
                    res_ids.append(passenger_obj.id)
            if not psg_exist:
                # Cek Booker sama dengan Passenger
                if [psg['title'], psg['first_name'], psg['last_name']] == [contact_obj.title, contact_obj.first_name, contact_obj.last_name]:
                    contact_obj.write(vals_for_update)
                    psg_exist = True
                    res_ids.append(contact_obj.id)

            if not psg_exist:
                if context['booker_type'] == 'COR/POR':
                    psg['passenger_on_partner_ids'] = [(4, context['sub_agent_id'])]
                    psg['agent_id'] = context['sub_agent_id']
                else:
                    psg['agent_id'] = context['agent_id']

                psg.update({
                    'commercial_agent_id': context['agent_id'],
                    'bill_to': '<span><b>{title} {first_name} {last_name}</b> <br>Phone:</span>'.format(**psg),
                })
                psg_obj = passenger_obj.create(psg)
                res_ids.append(psg_obj.id)
        return res_ids

    def create_booking(self, contact_data, passengers, option, search_request, file_upload, context, kwargs):
        try:
            self._validate_themespark(context, 'context')
            self._validate_themespark(search_request, 'header')
            try:
                agent_obj = self.env['tt.customer.details'].browse(int(contact_data['contact_id'])).agent_id
                if not agent_obj:
                    agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            except Exception:
                agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            context = self.update_api_context(agent_obj.id, context)

            if kwargs['force_issued']:
                is_enough = self.env['tt.agent'].check_balance_limit(agent_obj.id, kwargs['amount'])
                if not is_enough['error_code'] == 0:
                    raise Exception('BALANCE not enough')

            # ========= Validasi agent_id ===========
            # TODO : Security Issue VERY HIGH LEVEL
            # 1. Jika BUKAN is_company_website, maka contact.contact_id DIABAIKAN
            # 2. Jika ADA contact.contact_id MAKA agent_id = contact.contact_id.agent_id
            # 3. Jika TIDAK ADA contact.contact_id MAKA agent_id = co_uid.agent_id

            # PRODUCTION
            # self.validate_booking(api_context=context)
            user_obj = self.env['res.users'].sudo().browse(int(context['co_uid']))
            contact_data.update({
                'agent_id': user_obj.agent_id.id,
                'commercial_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
                'display_mobile': user_obj.mobile,
            })
            if user_obj.agent_id.agent_type_id.id in (self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
                if user_obj.agent_id.parent_agent_id:
                    contact_data.update({
                        'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
                        'booker_type': 'COR/POR',
                        'display_mobile': user_obj.mobile,
                    })

            header_val = self._themespark_header_normalization(search_request)
            contact_obj = self._create_contact(contact_data, context)

            psg_ids = self._evaluate_passenger_info(passengers, contact_obj.id, context['agent_id'])
            themespark_id = self.env['tt.master.themespark.lines'].sudo().search([('uuid', '=', search_request['product_type_uuid'])])

            booking_option = ''
            if option['perBooking']:
                for rec in option['perBooking']:
                    booking_option += rec['name'] + ': ' + str(rec['value']) + '\n'

            header_val.update({
                'contact_id': contact_obj.id,
                'display_mobile': contact_obj.mobile,
                'state': 'reserved',
                'agent_id': context['agent_id'],
                'user_id': context['co_uid'],
                'themespark_id': themespark_id.themespark_id.id,
                'visit_date': datetime.strptime(search_request['visit_date'], '%Y-%m-%d').strftime('%d %b %Y'),
                'themespark_name': themespark_id.themespark_id.name,
                'themespark_product': themespark_id.name,
                'themespark_product_uuid': search_request['product_type_uuid'],
                'booking_option': booking_option,
                'senior': search_request['senior'],
                'adult': search_request['adult'],
                'child': search_request['child'],
                'infant': search_request['infant'],
                'transport_type': 'activity',
                'provider': themespark_id.themespark_id.provider,
                'file_upload': file_upload,
            })

            if not themespark_id.instantConfirmation:
                header_val.update({
                    'information': 'On Request (max. 3 working days)',
                })

            # create header & Update SUB_AGENT_ID
            book_obj = self.sudo().create(header_val)

            # kwargs.update({
            #     'visit_date': search_request['visit_date'],
            # })

            for psg in passengers:
                vals = {
                    'themespark_booking_id': book_obj.id,
                    'passenger_id': psg['passenger_id'],
                    'pax_type': psg['pax_type'],
                    'pax_mobile': psg.get('mobile'),
                    'api_data': psg.get('api_data'),
                    # 'pricelist_id': book_obj.themespark_id.id
                }
                self.env['tt.themespark.booking.line'].sudo().create(vals)

            # for rec in service_charge_summary:
            #     rec.update({
            #         'themespark_booking_id': book_obj.id,
            #         'themespark_id': rec['pricelist_id'],
            #         'currency_id': self.env['res.currency'].search([('name', '=', rec['currency'])]).id
            #     })
            #     rec.pop('pricelist_id')
            #     rec.pop('currency')
            #     self.env['tt.themespark.booking.price'].sudo().create(rec)

            book_obj.sub_agent_id = contact_data['agent_id']

            book_obj.action_booked_themespark(context)
            context['order_id'] = book_obj.id
            if kwargs['force_issued']:
                book_obj.action_issued_themespark(context)

            self._create_passengers(passengers, contact_obj, context)

            self.env.cr.commit()
            return {
                'error_code': 0,
                'error_msg': 'Success',
                'response': {
                    'order_id': book_obj.id,
                    'order_number': book_obj.name,
                    'status': book_obj.state,
                }
            }
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e)
            }
