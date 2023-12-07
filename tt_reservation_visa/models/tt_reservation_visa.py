from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError
import logging
import traceback
import copy
import json
import base64
import pytz
from ...tools.api import Response
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
import hashlib

_logger = logging.getLogger(__name__)


# STATE_VISA = [
#     ('draft', 'Request'),
#     ('doc_check', 'Documents Check'),
#     ('doc_complete', 'Complete Document '),
#     ('confirm', 'Confirm to HO'),
#
#     ('partial_validate', 'Partial Validate'),
#     ('validate', 'Validated by HO'),
#     ('to_vendor', 'Send to Vendor'),
#     ('vendor_process', 'Proceed by Vendor'),
#     ('in_process', 'In Process'),
#     ('payment', 'Payment'),
#     ('process_by_consulate', 'Process by Consulate'),
#     ('partial_proceed', 'Partial Proceed'),
#     ('proceed', 'Proceed'),
#     ('partial_approve', 'Partial Approve'),
#     ('approve', 'Approve'),
#     ('reject', 'Rejected'),
#     ('delivered', 'Delivered'),
#     # ('ready', 'Sent'),
#     ('expired', 'Expired'),
#     ('fail_booked', 'Failed (Book)'),
#     ('cancel', 'Canceled'),
#     ('cancel2', 'Canceled'),
#     ('refund', 'Refund'),
#     ('done', 'Done'),
# ]

STATE_VISA = [
    ('draft', 'Request'),
    ('doc_check', 'Documents Check'),
    ('doc_complete', 'Complete Document '),
    ('confirm', 'Confirm to HO'),

    ('partial_validate', 'Partial Validate'),
    ('validate', 'Validated by HO'),
    ('in_process', 'Payment to HO'),
    ('to_vendor', 'Send to Vendor'),
    ('vendor_process', 'Proceed by Vendor'),
    ('payment', 'In Process'),
    ('process_by_consulate', 'Process by Consulate'),
    ('partial_proceed', 'Partial Proceed'),
    ('proceed', 'Proceed'),
    ('partial_approve', 'Partial Approve'),
    ('approve', 'Approve'),
    ('reject', 'Rejected'),
    ('delivered', 'Delivered'),
    # ('ready', 'Sent'),
    ('expired', 'Expired'),
    ('fail_booked', 'Failed (Book)'),
    ('cancel', 'Canceled'),
    ('cancel2', 'Canceled'),
    ('refund', 'Refund'),
    ('done', 'Done'),
]


class TtVisa(models.Model):
    _name = 'tt.reservation.visa'
    _inherit = 'tt.reservation'
    _order = 'name desc'
    _description = 'Reservation Visa'

    provider_type_id = fields.Many2one('tt.provider.type', string='Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_visa.tt_provider_type_visa'))

    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]})
    total_cost_price = fields.Monetary('Total Cost Price', default=0, readonly=True, compute="_compute_total_price")

    state_visa = fields.Selection(STATE_VISA, 'State', default='draft',
                                  help='''draft = requested
                                        confirm = HO accepted
                                        validate = if all required documents submitted and documents in progress
                                        cancel = request cancelled
                                        to_vendor = Documents sent to Vendor
                                        vendor_process = Documents proceed by Vendor
                                        in_process = in process by HO
                                        payment = payment to embassy
                                        process_by_consulate = process to consulate
                                        partial proceed = partial proceed by consulate
                                        proceed = proceed by consulate
                                        approved = approved by consulate
                                        delivered = Documents sent to agent
                                        done = Documents ready at agent or given to customer''')

    estimate_date = fields.Date('Estimate Date', help='Estimate Process Done since the required documents submitted',
                                readonly=True)
    use_vendor = fields.Boolean('Use Vendor', readonly=True, default=False)
    vendor_ids = fields.One2many('tt.reservation.visa.vendor.lines', 'visa_id', 'Expenses')

    document_to_ho_date = fields.Datetime('Document to HO Date', readonly=1)
    ho_validate_date = fields.Datetime('HO Validate Date', readonly=1)

    passenger_ids = fields.One2many('tt.reservation.visa.order.passengers', 'visa_id', 'Visa Order Passengers')

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    commercial_state = fields.Char('Payment Status', readonly=1, compute='_compute_commercial_state')  #
    confirmed_date = fields.Datetime('Confirmed Date', readonly=1)
    confirmed_uid = fields.Many2one('res.users', 'Confirmed By', readonly=1)

    validate_date = fields.Datetime('Validate Date', readonly=1)
    validate_uid = fields.Many2one('res.users', 'Validate By', readonly=1)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'visa_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.provider.visa', 'booking_id', string='Provider Booking')  # readonly=True, states={'cancel2': [('readonly', False)]}

    done_date = fields.Datetime('Done Date', readonly=1)

    to_vendor_date = fields.Datetime('Send To Vendor Date', readonly=1)
    vendor_process_date = fields.Datetime('Vendor Process Date', readonly=1)
    in_process_date = fields.Datetime('In Process Date', readonly=1)
    payment_date = fields.Datetime('Process By Consulate Date', readonly=1)
    process_by_consulate_date = fields.Datetime('Payement Date', readonly=1)
    partial_proceed_date = fields.Datetime('Partial proceed Date', readonly=1)
    proceed_date = fields.Datetime('Proceed Date', readonly=1)
    partial_approve_date = fields.Datetime('Partial Approve Date', readonly=1)
    approve_date = fields.Datetime('Approve Date', readonly=1)
    reject_date = fields.Datetime('Reject Date', readonly=1)
    delivered_date = fields.Datetime('Delivered Date', readonly=1)

    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)

    acquirer_id = fields.Many2one('payment.acquirer', 'Payment Method', readonly=True)

    proof_of_consulate = fields.Many2many('ir.attachment', string="Proof of Consulate")

    immigration_consulate = fields.Char('Immigration Consulate', readonly=1, compute="_compute_immigration_consulate")

    printout_handling_ho_id = fields.Many2one('tt.upload.center', readonly=True)
    printout_handling_customer_id = fields.Many2one('tt.upload.center', readonly=True)
    printout_itinerary_visa = fields.Many2one('tt.upload.center', 'Printout Itinerary', readonly=True)

    can_refund = fields.Boolean('Can Refund', default=False, readonly=True)
    ######################################################################################################
    # STATE
    ######################################################################################################

    def get_form_id(self):
        return self.env.ref("tt_reservation_visa.tt_reservation_visa_view_form")

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

    @api.multi
    def _compute_commercial_state(self):
        for rec in self:
            if rec.state == 'issued' or rec.issued_uid.id is not False:
                rec.commercial_state = 'Paid'
            else:
                rec.commercial_state = 'Unpaid'

    def action_fail_booked_visa(self):
        self.write({
            'state_visa': 'fail_booked',
            'state': 'fail_booked'
        })
        for psg in self.passenger_ids:
            psg.action_fail_booked()
        for pvdr in self.provider_booking_ids:
            pvdr.action_fail_booked_visa()
        self.message_post(body='Order FAILED (Booked)')

    def action_draft_visa(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 326')
        self.write({
            'state_visa': 'draft',
            'state': 'draft'
        })
        # saat mengubah state ke draft, akan mengubah semua state passenger ke draft
        for rec in self.passenger_ids:
            rec.action_draft()
        for rec in self.provider_booking_ids:
            rec.action_booked()
        self.message_post(body='Order DRAFT')

    def action_confirm_visa(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 327')
        is_confirmed = True
        for rec in self.passenger_ids:
            if rec.state not in ['confirm', 'cancel', 'validate']:
                is_confirmed = False

        if not is_confirmed:
            raise UserError(
                _('You have to Confirmed all The passengers document first.'))

        self.write({
            'state_visa': 'confirm',
            'state': 'booked',
            'confirmed_date': datetime.now(),
            'confirmed_uid': self.env.user.id
        })
        self.message_post(body='Order CONFIRMED')

    def action_partial_validate_visa(self):
        self.write({
            'state_visa': 'partial_validate'
        })
        self.message_post(body='Order PROCEED')

    def sync_status_btbo2(self, status):
        for credential in self.user_id.credential_ids.webhook_rel_ids:
            if "webhook/visa" in credential.url:
                ## check lebih efisien check api ccredential usernya punya webhook visa, atau kalau api user selalu di notify
                ## tetapi nanti filterny sendiri ke kirm ato enda

                data = {
                    'order_number': self.name,
                    'state': status,
                    'provider': 'rodextrip_visa'
                }
                vals = {
                    'provider_type': 'visa',
                    'action': 'sync_status_visa',
                    'action_todo': 'sync_status_visa',
                    'data': data,
                    'child_id': self.user_id.id
                }
                self.env['tt.api.webhook.data'].notify_subscriber(vals)
                break

    def action_validate_visa(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 328')
        is_validated = True
        for rec in self.passenger_ids:
            if rec.state not in ['validate', 'cancel']:
                is_validated = False

        if not is_validated:
            raise UserError(
                _('You have to Validated all The passengers document first.'))

        self.write({
            'state_visa': 'validate',
            'validate_date': datetime.now(),
            'validate_uid': self.env.user.id
        })
        self.sync_status_btbo2('validate')
        self.message_post(body='Order VALIDATED')

    def action_sync_status_visa_api(self, req):
        try:
            error_msg = ''
            if req.get('data'):
                book_id = self.env['tt.provider.visa'].search([('pnr2', '=', req['data'].get('order_number'))],
                                                              limit=1).booking_id #get book_id
                book_obj = self.env['tt.reservation.visa'].search([('id', '=', book_id.id)], limit=1) #ambil book obj
                # book_obj = self.env['tt.reservation.visa'].search([('name', '=', req['data']['order_number'])], limit=1) #local
                
                # login admin agar bisa get booking sudah check apikey hash di gateway jadi aman
                # tidak jadi login admin karena context selalu visa selalu buat cuman bisa jadi contoh
                # authorization = tools.config.get('backend_authorization', '')
                # credential = util.decode_authorization(authorization)
                # data = {
                #     'user': credential.get('username', ''),
                #     'password': credential.get('password', ''),
                #     'api_key': self.env['tt.api.credential'].search([('name', '=', 'gateway user'), ('api_role', '=', 'admin')], limit=1).api_key
                # }
                # get_credential = self.env['tt.api.credential'].get_credential_api(data, {'sid':''})
                # if get_credential['error_code']:
                #     ctx = get_credential['response']
                if req['data'].get('state') == 'validate':
                    self.action_validate_visa_by_api(book_obj)
                elif req['data'].get('state') == 'in_process':
                    self.action_in_process_visa_by_api(book_obj)
                elif req['data'].get('state') == 'payment':
                    self.action_payment_visa_by_api(book_obj)
                elif req['data'].get('state') == 'process_by_consulate':
                    self.action_process_by_consulate_visa_by_api(book_obj)
                elif req['data'].get('state') == 'proceed':
                    self.action_proceed_visa_by_api(book_obj)
                elif req['data'].get('state') == 'done':
                    self.action_done_visa_by_api(book_obj)
                elif req['data'].get('state') == 're_validate':
                    self.action_re_validate_visa_by_api(book_obj)
                elif req['data'].get('state') == 're_confirm':
                    self.action_re_confirm_visa_by_api(book_obj)
                elif req['data'].get('state') == 'cancel':
                    self.action_cancel_visa_by_api(book_obj)
                elif req['data'].get('state') == 'waiting':
                    self.action_waiting_visa_by_api(book_obj)
                elif req['data'].get('state') == 'rejected':
                    self.action_rejected_visa_by_api(book_obj)
                elif req['data'].get('state') == 'accept':
                    self.action_accept_visa_by_api(book_obj)
                elif req['data'].get('state') == 'to_HO':
                    self.action_to_HO_visa_by_api(book_obj)
                elif req['data'].get('state') == 'to_agent':
                    self.action_to_agent_visa_by_api(book_obj)
                else:
                    error_msg = 'data not found'
                    _logger.error("get credential error")
            if error_msg:
                return Response().get_error(error_msg, 500)
            else:
                return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)


    def action_validate_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_validate_api()
            book_obj.action_validate_visa()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_in_process_visa_by_api(self, book_obj):
        try:
            book_obj.action_in_process_visa()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_payment_visa_by_api(self, book_obj):
        try:
            book_obj.action_payment_visa()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_process_by_consulate_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_confirm_payment_api()
            book_obj.action_in_process_consulate_visa()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_re_validate_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_re_validate()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_re_confirm_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_re_confirm()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_cancel_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_cancel()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_waiting_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_waiting()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_proceed_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_proceed()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_rejected_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_reject()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_accept_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_accept()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_to_HO_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_to_HO()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_to_agent_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_to_agent()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_done_visa_by_api(self, book_obj):
        try:
            book_obj.passenger_ids.action_done()
            return Response().get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            return Response().get_error(error_message='contact b2b', error_code=500)

    def action_in_process_visa_button(self):
        return self.action_in_process_visa()

    def action_in_process_visa(self, pin=''):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 329')
        if self.env.user.is_using_pin and not pin:
            view = self.env.ref('tt_base.tt_input_pin_wizard_form_view')
            return {
                'name': 'Input Pin Wizard',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'tt.input.pin.wizard',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': {
                    'default_res_model': self._name,
                    'default_res_id': self.id
                }
            }

        data = {
            'order_number': self.name,
            'member': self.is_member,
            'acquirer_seq_id': self.payment_method,
            'agent_payment_method': self.payment_method_to_ho
        }
        if self.voucher_code:
            data.update({
                'voucher': {
                    'voucher_reference': self.voucher_code,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'provider_type': 'visa',
                    'provider': self.provider_name,
                },
            })
        website_use_point_reward = self.env['ir.config_parameter'].sudo().get_param('use_point_reward')
        if self.is_using_point_reward and website_use_point_reward == 'True':
            data.update({
                'use_point': self.is_using_point_reward
            })
        if self.env.user.is_using_pin:
            data.update({
                'pin': pin
            })
        ctx = {
            'co_agent_type_id': self.agent_type_id.id,
            'co_agent_id': self.agent_id.id,
            'co_uid': self.env.user.id
        }
        # co_uid diisi self.env.user.id supaya staff yg click yang di check pin, dan kalau salah pin yang di ban staff yang click

        payment_res = self.payment_reservation_api('visa', data, ctx) #visa, member, payment_seq_id
        if payment_res['error_code'] != 0:
            raise UserError(payment_res['error_msg'])
        self.write({
            'state_visa': 'in_process',
            'in_process_date': datetime.now()
        })

        for rec in self.passenger_ids:
            if rec.state in ['validate', 'cancel']:
                rec.action_in_process()
        context = {
            'co_uid': self.env.user.id
        }
        # self.action_booked_visa(context)
        self.action_issued_visa_api(data, context)
        # prepare vals for nta price in expenses
        provider_id = self.provider_booking_ids[0]
        expenses_vals = {
            'provider_id': provider_id.id,
            'visa_id': self.id,
            'reference_number': 'NTA',
            'nta_amount': self.total_nta,
        }
        provider_id.write({
            'vendor_ids': [(0, 0, expenses_vals)]
        })
        self.sync_status_btbo2('in_process')
        self.message_post(body='Order IN PROCESS')

    # kirim data dan dokumen ke vendor
    def action_to_vendor_visa(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 330')
        for provider in self.provider_booking_ids:
            provider.use_vendor = True
        self.write({
            'use_vendor': True,
            'state_visa': 'to_vendor',
            'to_vendor_date': datetime.now()
        })
        self.message_post(body='Order SENT TO VENDOR')

    def action_vendor_process_visa(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 331')
        self.write({
            'state_visa': 'vendor_process',
            'vendor_process_date': datetime.now()
        })
        self.message_post(body='Order VENDOR PROCESS')

    def action_payment_visa(self):
        self.write({
            'state_visa': 'payment',
            'payment_date': datetime.now()
        })
        self.sync_status_btbo2('payment')
        self.message_post(body='Order PAYMENT')

    def action_in_process_consulate_visa(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 332')
        is_payment = True
        for rec in self.passenger_ids:
            if rec.state not in ['confirm_payment']:
                is_payment = False

        if not is_payment:
            raise UserError(
                _('You have to pay all the passengers first.'))

        estimate_days = 0
        for psg in self.passenger_ids:
            if estimate_days < psg.pricelist_id.duration:
                estimate_days = psg.pricelist_id.duration

        self.write({
            'state_visa': 'process_by_consulate',
            'process_by_consulate_date': datetime.now(),
            'can_refund': False,
            'in_process_date': datetime.now(),
            'estimate_date': date.today() + timedelta(days=estimate_days)
        })
        self.sync_status_btbo2('process_by_consulate')
        self.message_post(body='Order IN PROCESS TO CONSULATE')
        for rec in self.passenger_ids:
            rec.action_in_process2()

    def action_proceed_visa(self):
        self.write({
            'state_visa': 'proceed',
            'proceed_date': datetime.now(),
        })
        self.message_post(body='Order PROCEED')

    def action_partial_proceed_visa(self):
        self.write({
            'state_visa': 'partial_proceed',
            'partial_proceed_date': datetime.now()
        })
        self.message_post(body='Order PARTIAL PROCEED')

    def action_approved_visa(self):
        self.write({
            'state_visa': 'approve',
            'approve_date': datetime.now()
        })
        self.message_post(body='Order APPROVED')

    def action_rejected_visa(self):
        self.write({
            'state_visa': 'reject',
            'reject_date': datetime.now()
        })
        self.message_post(body='Order REJECTED')

    def action_partial_approved_visa(self):
        self.write({
            'state_visa': 'partial_approve',
            'partial_approve_date': datetime.now()
        })
        self.message_post(body='Order PARTIAL APPROVED')

    def action_delivered_visa(self):
        """ Expenses wajib di isi untuk mencatat pengeluaran HO """
        for provider in self.provider_booking_ids:
            if not provider.vendor_ids:
                raise UserError(
                    _('You have to Fill Expenses.'))
        if self.state_visa != 'delivered':
            self.calc_visa_upsell_vendor()
            self.calc_visa_vendor()

        self.write({
            'state_visa': 'delivered',
            'delivered_date': datetime.now()
        })
        self.message_post(body='Order DELIVERED')

    def action_cancel_visa(self):
        # cek state visa.
        # jika state : in_process, partial_proceed, proceed, delivered, ready, done, create reverse ledger
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 333')
        if self.state_visa in ['in_process', 'payment']:
            self.can_refund = True
        if self.commercial_state == 'Unpaid':
            self.write({
                'use_vendor': False
            })
        # set semua state passenger ke cancel
        for rec in self.passenger_ids:
            rec.action_cancel()
        for rec in self.provider_booking_ids:
            rec.action_cancel()
            for vendor in rec.vendor_ids:
                vendor.sudo().unlink()
        self.write({
            'state_visa': 'cancel',
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'
        self.message_post(body='Order CANCELED')

    def action_done_visa(self):
        self.write({
            'state_visa': 'done',
            'done_date': datetime.now()
        })
        self.message_post(body='Order DONE')

    def action_expired(self):
        super(TtVisa, self).action_expired()
        self.state_visa = 'expired'

    def payment_visa_api(self, req, context):
        return self.payment_reservation_api('visa', req, context)

    def action_calc_expenses_visa(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 334')
        # Calc visa vendor
        self.calc_visa_upsell_vendor()
        # Create new agent invoice (panggil di agent sales visa)

    def calc_visa_upsell_vendor(self):
        diff_nta_upsell = 0
        total_charge = 0
        provider_code_list = []

        for provider in self.provider_booking_ids:
            if provider.provider_id.code not in provider_code_list:
                provider_code_list.append(provider.provider_id.code)
            for rec in provider.vendor_ids:
                if not rec.is_upsell_ledger_created and rec.amount != 0:
                    total_charge += rec.amount
                    diff_nta_upsell += (rec.amount - rec.nta_amount)
                    rec.is_upsell_ledger_created = True

        provider_code = ', '.join(provider_code_list)

        ledger = self.env['tt.ledger']
        if total_charge > 0:
            for rec in self:
                ledger.create_ledger_vanilla(
                    rec._name,
                    rec.id,
                    'Additional Charge Visa : ' + rec.name,
                    rec.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    2,
                    rec.currency_id.id,
                    rec.env.user.id,
                    rec.agent_id.id,
                    False,
                    0,
                    total_charge,
                    'Additional Charge Visa : ' + rec.name,
                    pnr=rec.pnr,
                    display_provider_name=provider_code,
                    provider_type_id=rec.provider_type_id.id
                )

        """ Jika diff nta upsell > 0 """
        if diff_nta_upsell > 0:
            ledger = self.env['tt.ledger']
            for rec in self:
                ho_obj = rec.agent_id.ho_id
                ledger.create_ledger_vanilla(
                    rec._name,
                    rec.id,
                    'NTA Upsell Visa : ' + rec.name,
                    rec.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    3,
                    rec.currency_id.id,
                    rec.env.user.id,
                    ho_obj and ho_obj.id or False,
                    False,
                    diff_nta_upsell,
                    0,
                    'NTA Upsell Visa : ' + rec.name,
                    pnr=rec.pnr,
                    display_provider_name=provider_code,
                    provider_type_id=rec.provider_type_id.id
                )
        elif diff_nta_upsell < 0:
            """ Jika diff nta upsell < 0 """
            ledger = self.env['tt.ledger']
            for rec in self:
                ho_obj = rec.agent_id.ho_id
                ledger.create_ledger_vanilla(
                    rec._name,
                    rec.id,
                    'NTA Upsell Visa : ' + rec.name,
                    rec.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    3,
                    rec.currency_id.id,
                    rec.env.user.id,
                    ho_obj and ho_obj.id or False,
                    False,
                    0,
                    diff_nta_upsell,
                    'NTA Upsell Visa : ' + rec.name,
                    pnr=rec.pnr,
                    display_provider_name=provider_code,
                    provider_type_id=rec.provider_type_id.id
                )

    def calc_visa_vendor(self):
        """ Mencatat expenses ke dalam ledger visa """

        """ Hitung total expenses (pengeluaran) """
        total_expenses = 0
        provider_code_list = []

        for provider in self.provider_booking_ids:
            if provider.provider_id.code not in provider_code_list:
                provider_code_list.append(provider.provider_id.code)
            for rec in provider.vendor_ids:
                if rec.amount == 0:
                    total_expenses += rec.nta_amount

        provider_code = ', '.join(provider_code_list)

        """ Hitung total nta per pax """
        nta_price = 0
        for pax in self.passenger_ids:
            if pax.state != 'cancel':
                nta_price += pax.pricelist_id.nta_price

        """ hitung profit HO dg mengurangi harga NTA dg total pengeluaran """
        ho_profit = nta_price - total_expenses

        """ Jika profit HO > 0 (untung) """
        if ho_profit > 0:
            ledger = self.env['tt.ledger']
            for rec in self:
                doc_type = []
                for sc in rec.sale_service_charge_ids:
                    if not sc.pricelist_id.visa_type in doc_type:
                        doc_type.append(sc.pricelist_id.visa_type)

                doc_type = ','.join(str(e) for e in doc_type)
                ho_obj = rec.agent_id.ho_id
                ledger.create_ledger_vanilla(
                    rec._name,
                    rec.id,
                    'Profit ' + doc_type + ' : ' + rec.name,
                    rec.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    3,
                    rec.currency_id.id,
                    rec.env.user.id,
                    ho_obj and ho_obj.id or False,
                    False,
                    ho_profit,
                    0,
                    'Profit HO Visa : ' + rec.name,
                    pnr=rec.pnr,
                    display_provider_name=provider_code,
                    provider_type_id=rec.provider_type_id.id
                )
        """ Jika profit HO < 0 (rugi) """
        if ho_profit < 0:
            ledger = self.env['tt.ledger']
            for rec in self:
                doc_type = []
                for sc in rec.sale_service_charge_ids:
                    if not sc.pricelist_id.visa_type in doc_type:
                        doc_type.append(sc.pricelist_id.visa_type)

                doc_type = ','.join(str(e) for e in doc_type)
                ho_obj = rec.agent_id.ho_id
                ledger.create_ledger_vanilla(
                    rec._name,
                    rec.id,
                    'Additional Charge ' + doc_type + ' : ' + rec.name,
                    rec.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    3,
                    rec.currency_id.id,
                    rec.env.user.id,
                    ho_obj and ho_obj.id or False,
                    False,
                    0,
                    abs(ho_profit),
                    'Additional Charge Visa : ' + rec.name,
                    pnr=rec.pnr,
                    display_provider_name=provider_code,
                    provider_type_id=rec.provider_type_id.id
                )

    def change_pnr_api(self, data, context):
        book_obj = self.env['tt.reservation.visa'].search([('name', '=', data.get('order_number'))], limit=1)
        if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1):
            for vendor in book_obj['provider_booking_ids']:
                vendor.pnr2 = data['pnr']
                vendor.provider_id = self.env['tt.provider'].search([('code', '=', data['provider'])], limit=1).id
            #ganti yang dalam vendor + tambah provider
            return True
        return False

    def get_booking_visa_api(self, data, context):  #
        try:
            _logger.info("Get req\n" + json.dumps(context))
            book_obj = self.env['tt.reservation.visa'].search([('name', '=', data.get('order_number'))], limit=1)
            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                raise RequestException(1008)
            # if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1) or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids:
            # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
            _co_user = self.env['res.users'].sudo().browse(int(context['co_uid']))
            if book_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_erp_manager'):
                res_dict = book_obj.sudo().to_dict(context)
                passenger = []
                requirement_check = True
                for idx, pax in enumerate(book_obj.passenger_ids, 0):
                    requirement = []
                    interview = {
                        'needs': pax.interview
                    }
                    biometrics = {
                        'needs': pax.biometrics
                    }
                    channel_service_charges = {}
                    if len(pax.channel_service_charge_ids.ids) > 0:
                        channel_service_charges = pax.get_channel_service_charges()
                    sale_service_charges = pax.get_service_charges()
                    service_charge_details = pax.get_service_charge_details()

                    """ Requirements """
                    for require in pax.to_requirement_ids:
                        if require.is_copy == False and require.is_ori == False:
                            requirement_check = False
                        requirement.append({
                            'name': require.requirement_id.name,
                            'is_copy': require.is_copy,
                            'is_original': require.is_ori
                        })
                    """ Interview """
                    interview_list = []
                    if pax.interview is True:
                        for intvw in pax.interview_ids:
                            interview_list.append({
                                'datetime': str(intvw.datetime),
                                'ho_employee': intvw.ho_employee,
                                'meeting_point': intvw.meeting_point,
                                'location': intvw.location_interview_id
                            })
                    interview['interview_list'] = interview_list
                    """ Biometrics """
                    biometrics_list = []
                    if pax.biometrics is True:
                        for bio in pax.biometrics_ids:
                            biometrics_list.append({
                                'datetime': str(bio.datetime),
                                'ho_employee': bio.ho_employee,
                                'meeting_point': bio.meeting_point,
                                'location': bio.location_biometrics_id
                            })
                    biometrics['biometrics_list'] = biometrics_list

                    """ PROVIDER BOOKING IDS"""
                    prov_list = []
                    for rec in book_obj.provider_booking_ids:
                        prov_list.append(rec.to_dict())

                    pax_type = ''
                    for pnr in sale_service_charges:
                        for svc in sale_service_charges[pnr]:
                            pax_type = sale_service_charges[pnr][svc]['pax_type']
                            break
                        break

                    passenger.append({
                        'title': pax.title,
                        'first_name': pax.first_name,
                        'last_name': pax.last_name,
                        'name': '%s %s' % (pax.first_name, pax.last_name),
                        'birth_date': str(pax.birth_date),
                        'gender': pax.gender,
                        'age': pax.age.split(' ')[0][:-1],
                        'passport_number': pax.passport_number or '',
                        'passport_expdate': str(pax.passport_expdate) or '',
                        'visa': {
                            'entry_type': dict(pax.pricelist_id._fields['entry_type'].selection).get(
                                pax.pricelist_id.entry_type) if pax.pricelist_id else '',
                            'visa_type': dict(pax.pricelist_id._fields['visa_type'].selection).get(
                                pax.pricelist_id.visa_type) if pax.pricelist_id else '',
                            'process': dict(pax.pricelist_id._fields['process_type'].selection).get(
                                pax.pricelist_id.process_type) if pax.pricelist_id else '',
                            'pax_type': pax.pricelist_id.pax_type if pax.pricelist_id else '',
                            'duration': pax.pricelist_id.duration if pax.pricelist_id else '',
                            'immigration_consulate': pax.pricelist_id.immigration_consulate if pax.pricelist_id else '',
                            'requirement': requirement,
                            'interview': interview,
                            'biometrics': biometrics
                        },
                        'channel_service_charges': channel_service_charges,
                        'sale_service_charges': sale_service_charges,
                        'service_charge_details': service_charge_details,
                        'pax_type': pax_type,
                        'sequence': idx
                    })
                state_visa = {}
                for rec in STATE_VISA:
                    if rec[0] == 'expired':
                        break
                    if rec[0] == 'draft' or rec[0] == 'doc_check':
                        state_visa.update({
                            rec[0]: {
                                "name": rec[1],
                                "value": True,
                                'date': book_obj.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                            }
                        })
                    else:
                        state_visa.update({
                            rec[0]: {
                                "name": rec[1],
                                "value": False
                            }
                        })

                if requirement_check:
                    state_visa['doc_complete'].update({
                        "value": True,
                        'date': book_obj.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                    })
                if book_obj.confirmed_date != False:
                    state_visa['confirm'].update({
                        "value": True,
                        'date': book_obj.confirmed_date.strftime("%Y-%m-%d %H:%M:%S"),
                        'confirm': book_obj.confirmed_uid.name
                    })
                if book_obj.validate_date != False:
                    state_visa['partial_validate'].update({
                        "value": True,
                        'date': book_obj.validate_date.strftime("%Y-%m-%d %H:%M:%S"),
                        'confirm': book_obj.validate_uid.name
                    })
                if book_obj.to_vendor_date != False:
                    state_visa['to_vendor'].update({
                        "value": True,
                        'date': book_obj.to_vendor_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
                if book_obj.vendor_process_date != False:
                    state_visa['vendor_process'].update({
                        "value": True,
                        'date': book_obj.vendor_process_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
                if book_obj.in_process_date != False:
                    state_visa['in_process'].update({
                        "value": True,
                        'date': book_obj.in_process_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
                if book_obj.payment_date != False:
                    state_visa['payment'].update({
                        "value": True,
                        'date': book_obj.payment_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
                if book_obj.process_by_consulate_date != False:
                    state_visa['process_by_consulate'].update({
                        "value": True,
                        'date': book_obj.process_by_consulate_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
                if book_obj.partial_proceed_date != False:
                    state_visa['partial_proceed'].update({
                        "value": True,
                        'date': book_obj.partial_proceed_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
                if book_obj.proceed_date != False:
                    state_visa['proceed'].update({
                        "value": True,
                        'date': book_obj.proceed_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
                if book_obj.partial_approve_date != False:
                    state_visa['partial_approve'].update({
                        "value": True,
                        'date': book_obj.partial_approve_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
                if book_obj.approve_date != False:
                    state_visa['approve'].update({
                        "value": True,
                        'date': book_obj.approve_date.strftime("%Y-%m-%d %H:%M:%S")
                    })
                if book_obj.reject_date != False:
                    state_visa['reject'].update({
                        "value": True,
                        'date': book_obj.reject_date.strftime("%Y-%m-%d %H:%M:%S")
                    })

                if book_obj.state_visa == 'expired':
                    state_visa.update({
                        STATE_VISA[17][0]: {
                            "name": STATE_VISA[15][1],
                            "value": True, 'date': ''
                        }
                    })
                elif book_obj.state_visa == 'fail_booked':
                    state_visa.update({
                        STATE_VISA[18][0]: {
                            "name": STATE_VISA[16][1],
                            "value": True, 'date': ''
                        }
                    })
                elif book_obj.state_visa == 'cancel':
                    state_visa.update({
                        STATE_VISA[19][0]: {
                            "name": STATE_VISA[17][1],
                            "value": True,
                            'date': ''
                        }
                    })
                elif book_obj.state_visa == 'cancel2':
                    state_visa.update({
                        STATE_VISA[20][0]: {
                            "name": STATE_VISA[18][1],
                            "value": True,
                            'date': ''
                        }
                    })
                elif book_obj.state_visa == 'refund':
                    state_visa.update({
                        STATE_VISA[21][0]: {
                            "name": STATE_VISA[19][1],
                            "value": True,
                            'date': ''
                        }
                    })
                elif book_obj.state_visa == 'done':
                    state_visa.update({
                        STATE_VISA[22][0]: {
                            "name": STATE_VISA[20][1],
                            "value": True,
                            'date': book_obj.done_date.strftime("%Y-%m-%d %H:%M:%S")
                        }
                    })
                else:
                    state_visa.update({
                        STATE_VISA[22][0]: {
                            "name": STATE_VISA[20][1],
                            "value": False,
                            'date': ''
                        }
                    })
                res_dict.pop('book_id')
                res_dict.pop('agent_id')
                res_dict.update({
                    'contact': {
                        'title': res_dict['contact']['title'],
                        'name': res_dict['contact']['name'],
                        'email': res_dict['contact']['email'],
                        'phone': res_dict['contact']['phone']
                    },
                    'journey': {
                        'country': book_obj.country_id.name,
                        'departure_date': str(res_dict['departure_date']),
                        'in_process_date': str(book_obj['in_process_date'].strftime("%Y-%m-%d")) if book_obj[
                            'in_process_date'] else '',
                        'name': res_dict['order_number'],
                        'payment_status': book_obj.commercial_state,
                        'state': res_dict['state'],
                        'state_visa': dict(book_obj._fields['state_visa'].selection).get(book_obj.state_visa)
                    },
                    'passengers': passenger,
                    'state_visa_arr': state_visa,
                    'provider_bookings': prov_list
                })
                _logger.info("Get resp\n" + json.dumps(res_dict))
                return Response().get_no_error(res_dict)
            else:
                raise RequestException(1035)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013, additional_message='There\'s something wrong.')

    def state_booking_visa_api(self,data, context):
        book_obj = self.env['tt.reservation.visa'].search([('name', '=', data.get('order_number'))], limit=1)
        if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1):
            if data['state'] == 'booked':
                book_obj.action_booked_visa(context)
            elif data['state'] == 'failed':
                book_obj.action_fail_booked_visa()

    # def create_booking_visa_api(self, data, context):  #
    #     sell_visa = data['sell_visa']  # self.param_sell_visa
    #     booker = data['booker']  # self.param_booker
    #     contact = data['contact']  # self.param_contact
    #     passengers = copy.deepcopy(data['passenger'])  # self.param_passenger
    #     search = data['search']  # self.param_search
    #     payment = data['payment']  # self.param_payment
    #     context = context  # self.param_context
    #     voucher = data['voucher']  # self.param_voucher
    #     try:
    #         # cek saldo
    #         total_price = 0
    #         for psg in passengers:
    #             visa_pricelist_obj = self.env['tt.reservation.visa.pricelist'].search([('reference_code', '=', psg['master_visa_Id'])])
    #             if visa_pricelist_obj:
    #                 total_price += visa_pricelist_obj.sale_price
    #
    #         user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
    #
    #         header_val = {}
    #
    #         booker_id = self.create_booker_api(booker, context)
    #         contact_id = self.create_contact_api(contact[0], booker_id, context)
    #         passenger_ids = self.create_customer_api(passengers, context, booker_id, contact_id)  # create passenger
    #
    #         to_psg_ids = self._create_visa_order(passengers, passenger_ids, context)  # create visa order data['passenger']
    #         if to_psg_ids['error_code'] == 0:
    #             psg_ids = to_psg_ids['response']
    #         else:
    #             return to_psg_ids  # Return error code & msg
    #
    #         pricing = self.create_sale_service_charge_value(passengers, psg_ids, context, sell_visa)  # create pricing dict
    #
    #         voucher = ''
    #         if data['voucher']:
    #             voucher = data['voucher']['voucher_reference']
    #
    #         header_val.update({
    #             'departure_date': datetime.strptime(search['departure_date'], '%Y-%m-%d').strftime('%d/%m/%Y'),
    #             'country_id': self.env['res.country'].sudo().search([('name', '=', search['destination'])], limit=1).id,
    #             'booker_id': booker_id.id,
    #             'voucher_code': voucher,
    #             'is_member': payment['member'],
    #             'payment_method': payment['acquirer_seq_id'],
    #             'payment_active': True,
    #             'contact_title': contact[0]['title'],
    #             'contact_id': contact_id.id,
    #             'contact_name': contact[0]['first_name'] + ' ' + contact[0]['last_name'],
    #             'contact_email': contact_id.email,
    #             'contact_phone': "%s - %s" % (contact_id.phone_ids[0].calling_code,contact_id.phone_ids[0].calling_number),
    #             'passenger_ids': [(6, 0, psg_ids)],
    #             'adult': sell_visa['pax']['adult'],
    #             'child': sell_visa['pax']['child'],
    #             'infant': sell_visa['pax']['infant'],
    #             'state': 'booked',
    #             'agent_id': context['co_agent_id'],
    #             'customer_parent_id': context.get('co_customer_parent_id', False),
    #             'user_id': context['co_uid'],
    #         })
    #
    #         book_obj = self.sudo().create(header_val)
    #
    #         for psg in book_obj.passenger_ids:
    #             for scs in psg.cost_service_charge_ids:
    #                 scs['description'] = book_obj.name
    #
    #         book_obj.document_to_ho_date = datetime.now() + timedelta(days=1)
    #         book_obj.ho_validate_date = datetime.now() + timedelta(days=3)
    #         book_obj.hold_date = datetime.now() + timedelta(days=31)
    #
    #         book_obj.pnr = book_obj.name
    #
    #         book_obj.write({
    #             'state_visa': 'confirm',
    #             'confirmed_date': datetime.now(),
    #             'confirmed_uid': context['co_uid']
    #         })
    #         book_obj.message_post(body='Order CONFIRMED')
    #
    #         self._calc_grand_total()
    #
    #         country_obj = self.env['res.country']
    #         provider_obj = self.env['tt.provider']
    #
    #         provider = provider_obj.env['tt.provider'].search([('code', '=', sell_visa['provider'])], limit=1)
    #         country = country_obj.search([('name', '=', search['destination'])], limit=1)
    #
    #         vals = {
    #             'booking_id': book_obj.id,
    #             'pnr': book_obj.name,
    #             'provider_id': provider.id,
    #             'country_id': country.id,
    #             'departure_date': datetime.strptime(search['departure_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
    #         }
    #         provider_visa_obj = book_obj.env['tt.provider.visa'].sudo().create(vals)
    #
    #         book_obj.get_list_of_provider_visa()
    #
    #         for psg in book_obj.passenger_ids:
    #             vals = {
    #                 'provider_id': provider_visa_obj.id,
    #                 'passenger_id': psg.id,
    #                 'pax_type': psg.passenger_type,
    #                 'pricelist_id': psg.pricelist_id.id
    #             }
    #             self.env['tt.provider.visa.passengers'].sudo().create(vals)
    #
    #         provider_visa_obj.delete_service_charge()
    #         provider_visa_obj.create_service_charge(pricing)
    #         book_obj.calculate_service_charge()
    #
    #         book_obj.action_booked_visa(context)
    #
    #         response = {
    #             'order_number': book_obj.name
    #         }
    #         res = self.get_booking_visa_api(response, context)
    #         return res
    #     except RequestException as e:
    #         _logger.error(traceback.format_exc())
    #         try:
    #             book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
    #         except:
    #             _logger.error('Creating Notes Error')
    #         return e.error_dict()
    #     except Exception as e:
    #         _logger.error(traceback.format_exc())
    #         try:
    #             book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc() + '\n'
    #         except:
    #             _logger.error('Creating Notes Error')
    #         self.env.cr.rollback()
    #         return ERR.get_error(1004, additional_message='There\'s something wrong.')

    def create_booking_visa_api(self, req, context):
        _logger.info("Create\n" + json.dumps(req))
        booker = req['booker']
        contacts = req['contacts']
        passengers = req['passengers']
        booking_data = req['search']
        sell_visa = req['sell_visa']
        payment = req['acquirer_seq_id']  # self.param_payment
        voucher = ''
        is_using_point_reward = req.get('use_point')
        if req.get('voucher'):
            voucher = req['voucher']['voucher_reference']
        try:
            values = self._prepare_booking_api(booking_data,sell_visa,context)
            booker_obj = self.create_booker_api(booker,context)
            contact_obj = self.create_contact_api(contacts[0],booker_obj,context)

            list_passenger_value = self.create_passenger_value_api(passengers)
            list_customer_id = self.create_customer_api(passengers,context,booker_obj.seq_id,contact_obj.seq_id)

            to_psg_ids = self._create_visa_order(passengers, list_passenger_value, context)  # create visa order data['passenger']
            if to_psg_ids['error_code'] == 0:
                psg_ids = to_psg_ids['response']
            else:
                return to_psg_ids  # Return error code & msg
            #fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
            # for idx,rec in enumerate(list_passenger_value):
            #     rec[2].update({
            #         'customer_id': list_customer_id[idx].id,
            #     })
            #
            # for psg in list_passenger_value:
            #     util.pop_empty_key(psg[2])

            ## 22 JUN 2023 - IVAN
            ## GET CURRENCY CODE
            currency = ''
            currency_obj = None
            for provider in sell_visa['provider_bookings']:
                for svc_summary in provider['service_charge_summary']:
                    for svc in svc_summary['service_charges']:
                        currency = svc['currency']
            if currency:
                currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
                # if currency_obj:
                #     book_obj.currency_id = currency_obj.id

            values.update({
                'user_id': context['co_uid'],
                'sid_booked': context['signature'],
                'booker_id': booker_obj.id,
                'contact_title': contacts[0]['title'],
                'contact_id': contact_obj.id,
                'contact_name': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': contact_obj.phone_ids and "%s - %s" % (contact_obj.phone_ids[0].calling_code,contact_obj.phone_ids[0].calling_number) or '-',
                'passenger_ids': [(6, 0, psg_ids)],
                # 'passenger_ids': list_passenger_value,
                'payment_method': payment,
                'payment_active': True,
                'voucher_code': voucher,
                'is_using_point_reward': is_using_point_reward,
                'currency_id': currency_obj.id if currency and currency_obj else self.env.user.company_id.currency_id.id
            })

            book_obj = self.create(values)
            book_obj.write({
                'state_visa': 'confirm',
                'confirmed_date': datetime.now(),
                'confirmed_uid': context['co_uid'],
                'pnr': book_obj.name
            })
            for provider_obj in book_obj.provider_booking_ids:
                provider_obj.create_ticket_api(passengers)
                provider_obj.pnr = book_obj.name
                total_price = 0
                service_charges_val = []
                visa_list = []
                for pax in passengers:
                    add = True
                    for visa in visa_list:
                        if pax['master_visa_Id'] == visa['id']:
                            add = False
                            visa['pax_count'] += 1
                    if add:
                        for visa in sell_visa['search_data']:
                            if visa['id'] == pax['master_visa_Id']:
                                visa_list.append({
                                    'id': visa['id'],
                                    'pax_count': 1,
                                    'service_charge_summary': visa['service_charge_summary']
                                })
                                break

                for idx,psg in enumerate(book_obj.passenger_ids):
                    vals = {
                        'provider_id': provider_obj.id,
                        'passenger_id': psg.id,
                        'pax_type': psg.passenger_type,
                        'pricelist_id': psg.pricelist_id.id
                    }
                    provider_obj.passenger_ids.create(vals)
                    psg.update({
                        'price_list_code': passengers[idx]['master_visa_Id']
                    })

                for visa in visa_list:
                    for svc_summary in visa['service_charge_summary']:
                        for svc in svc_summary['service_charges']:
                            ## currency di skip default ke company
                            service_charges_val.append({
                                "pax_type": svc['pax_type'],
                                "pax_count": visa['pax_count'],
                                "amount": svc['amount'],
                                "total_amount": svc['amount'] * visa['pax_count'],
                                "foreign_amount": svc['foreign_amount'],
                                "charge_code": svc['charge_code'],
                                "charge_type": svc['charge_type'],
                                "commission_agent_id": svc.get('commission_agent_id', False),
                                "price_list_code": visa.get('id')
                            })
                            total_price += svc['amount'] * visa['pax_count']

                provider_obj.create_service_charge(service_charges_val)
                provider_obj.total_price = total_price

            book_obj.calculate_service_charge()
            book_obj.check_provider_state(context)

            response_provider_ids = []
            for provider in book_obj.provider_booking_ids:
                response_provider_ids.append({
                    'id': provider.id,
                    'code': provider.provider_id.code,
                })

            #channel repricing upsell
            if req.get('repricing_data'):
                req['repricing_data']['order_number'] = book_obj.name
                self.env['tt.reservation'].channel_pricing_api(req['repricing_data'], context)
                book_obj.create_svc_upsell()

            response = {
                'order_number': book_obj.name
            }
            res = self.get_booking_visa_api(response, context)
            response = {
                'book_id': book_obj.id,
                'order_number': book_obj.name,
                'provider_ids': response_provider_ids,
                'journey': res['response']['journey']
            }
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

    def _prepare_booking_api(self, booking_data, sell_visa, context_gateway):
        country_obj = self.env['res.country']
        provider_obj = self.env['tt.provider']

        # "pax_type": "ADT",
        # "pax_count": 1,
        # "amount": 150000,
        # "total_amount": 150000,
        # "foreign_amount": 150000,
        # "currency": "IDR",
        # "foreign_currency": "IDR",
        # "charge_code": "fare",
        # "charge_type": "FARE"

        provider_vals = []
        country = country_obj.search([('name', '=', booking_data['destination'])], limit=1)
        pax = {
            "adult": 0,
            "child": 0,
            "infant": 0
        }
        for rec in sell_visa['provider_bookings']:
            provider = provider_obj.env['tt.provider'].search([('code', '=', rec['provider'])], limit=1)
            provider_type_id = self.env.ref('tt_reservation_visa.tt_provider_type_visa')
            provider_obj = self.env['tt.provider'].sudo().search([('code', '=', rec['provider']), ('provider_type_id', '=', provider_type_id.id)], limit=1)

            provider_vals = {
                'state': 'booked',
                'provider_id': provider.id,
                'country_id': country.id,
                'departure_date': datetime.strptime(booking_data['departure_date'], '%Y-%m-%d').strftime('%d/%m/%Y'),
                'hold_date': datetime.now() + timedelta(days=31),
                'booked_uid': context_gateway['co_uid'],
                'booked_date': fields.Datetime.now()
            }
            for pax_type in rec['pax']:
                pax[pax_type] += rec['pax'][pax_type]

        booking_tmp = {
            'state': 'booked',
            'provider_type_id': provider_type_id.id,
            'ho_id': context_gateway['co_ho_id'],
            'agent_id': context_gateway['co_agent_id'],
            'customer_parent_id': context_gateway.get('co_customer_parent_id',False),
            'user_id': context_gateway['co_uid'],
            'provider_name': provider_obj.code,
            'country_id': country.id,
            'hold_date': datetime.now() + timedelta(days=31),
            'departure_date': datetime.strptime(booking_data['departure_date'], '%Y-%m-%d').strftime('%d/%m/%Y'),
            'provider_booking_ids': [(0,0,provider_vals)],
            'booked_uid': context_gateway['co_uid'],
            'booked_date': fields.Datetime.now(),
            'adult': pax['adult'],
            'child': pax['child'],
            'infant': pax['infant']
        }
        return booking_tmp

    # to generate sale service charge
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
                    if p_charge_code == 'csc':
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
                        'booking_visa_id': self.id,
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

    def create_sale_service_charge_value(self, passenger, passenger_ids, context, sell_visa):
        ssc_list = []
        ssc_list_2 = []

        pricelist_env = self.env['tt.reservation.visa.pricelist'].sudo()
        passenger_env = self.env['tt.reservation.visa.order.passengers']

        for idx, psg in enumerate(passenger):
            ssc = []
            pricelist_id = self.env['tt.reservation.visa.pricelist'].search([('reference_code', '=', psg['master_visa_Id'])]).id
            pricelist_obj = pricelist_env.browse(pricelist_id)
            passenger_obj = passenger_env.browse(passenger_ids[idx])

            sale_price = 0
            for sell in sell_visa['search_data']:
                if 'id' in sell and str(sell['id']) == psg['master_visa_Id']:
                    if 'sale_price' in sell:
                        if 'total_price' in sell['sale_price']:
                            sale_price = sell['sale_price'].get('total_price')
                    break

            vals = {
                'amount': sale_price,
                'charge_code': 'fare',
                'charge_type': 'TOTAL',
                'passenger_visa_id': passenger_ids[idx],
                'description': pricelist_obj.description,
                'pax_type': pricelist_obj.pax_type,
                'currency_id': pricelist_obj.currency_id.id,
                'pax_count': 1,
                'total': pricelist_obj.sale_price,
                'pricelist_id': pricelist_id,
                'sequence': passenger_obj.sequence,
            }
            ssc_list.append(vals)
            # ssc_obj = passenger_obj.cost_service_charge_ids.create(vals)
            # ssc_obj.write({
            #     'passenger_visa_ids': [(6, 0, passenger_obj.ids)]
            # })
            # ssc.append(ssc_obj.id)

            commission_list2 = []
            for sell in sell_visa['search_data']:
                if 'id' in sell and str(sell['id']) == psg['master_visa_Id']:
                    if 'commission' in sell:
                        commission_list2 = sell.get('commission')
                    break
            if commission_list2:
                for comm in commission_list2:
                    vals2 = vals.copy()
                    vals2.update({
                        'commission_agent_id': comm['commission_agent_id'],
                        'total': comm['amount'],
                        'amount': comm['amount'],
                        'charge_code': comm['charge_code'],
                        'charge_type': 'RAC',
                    })
                    ssc_list.append(vals2)
                    # ssc_obj2 = passenger_obj.cost_service_charge_ids.create(vals2)
                    # ssc_obj2.write({
                    #     'passenger_visa_ids': [(6, 0, passenger_obj.ids)]
                    # })
                    # ssc.append(ssc_obj2.id)

            # passenger_obj.write({
            #     'cost_service_charge_ids': [(6, 0, ssc)]
            # })
            vals_fixed = {
                'commission_agent_id': pricelist_obj.ho_id and pricelist_obj.ho_id.id or False,
                'amount': -(pricelist_obj.cost_price - pricelist_obj.nta_price),
                'charge_code': 'fixed',
                'charge_type': 'RAC',
                'passenger_visa_id': passenger_ids[idx],
                'description': pricelist_obj.description,
                'pax_type': pricelist_obj.pax_type,
                'currency_id': pricelist_obj.currency_id.id,
                'pax_count': 1,
                'total': -(pricelist_obj.cost_price - pricelist_obj.nta_price),
                'pricelist_id': pricelist_id,
                'sequence': passenger_obj.sequence,
            }
            ssc_list.append(vals_fixed)
            # ssc_obj3 = passenger_obj.cost_service_charge_ids.create(vals_fixed)
            # ssc_obj3.write({
            #     'passenger_visa_ids': [(6, 0, passenger_obj.ids)]
            # })
            # ssc.append(ssc_obj3.id)

            # passenger_obj.write({
            #     'cost_service_charge_ids': [(6, 0, ssc)]
            # })

        # susun daftar ssc yang sudah dibuat
        for ssc in ssc_list:
            # compare with ssc_list
            ssc_same = False
            for ssc_2 in ssc_list_2:
                if ssc['pricelist_id'] == ssc_2['pricelist_id']:
                    if ssc['charge_code'] == ssc_2['charge_code']:
                        if ssc['pax_type'] == ssc_2['pax_type']:
                            ssc_same = True
                            # update ssc_final
                            ssc_2['pax_count'] = ssc_2['pax_count'] + 1,
                            ssc_2['passenger_visa_ids'].append(ssc['passenger_visa_id'])
                            ssc_2['total'] += ssc.get('amount')
                            ssc_2['pax_count'] = ssc_2['pax_count'][0]
                            break
            if ssc_same is False:
                vals = {
                    'amount': ssc['amount'],
                    'charge_code': ssc['charge_code'],
                    'charge_type': ssc['charge_type'],
                    'passenger_visa_ids': [],
                    'description': ssc['description'],
                    'pax_type': ssc['pax_type'],
                    'currency_id': ssc['currency_id'],
                    'pax_count': 1,
                    'total': ssc['total'],
                    'pricelist_id': ssc['pricelist_id']
                }
                if 'commission_agent_id' in ssc:
                    vals.update({
                        'commission_agent_id': ssc['commission_agent_id']
                    })
                vals['passenger_visa_ids'].append(ssc['passenger_visa_id'])
                ssc_list_2.append(vals)

        return ssc_list_2

    def _create_visa_order(self, passengers, passenger_ids, context):
        try:
            to_psg_env = self.env['tt.reservation.visa.order.passengers'].sudo()
            to_req_env = self.env['tt.reservation.visa.order.requirements'].sudo()
            to_psg_list = []

            for idx, psg in enumerate(passengers):
                if 'master_visa_Id' not in psg:
                    """ Kalau reference code kosong, raise RequestException """
                    raise RequestException(1004,
                                           additional_message='Error create Passenger Visa : Reference Code is Empty.')
                pricelist_id = self.env['tt.reservation.visa.pricelist'].search([('reference_code', '=', psg['master_visa_Id'])]).id
                if pricelist_id is False:
                    raise RequestException(1004,
                                           additional_message='Error create Passenger Visa : Reference Code not Found.')
                psg_vals = passenger_ids[idx][2]
                psg_vals.update({
                    'title': psg['title'],
                    'pricelist_id': pricelist_id,
                    'passenger_type': psg['pax_type'],
                    'notes': psg.get('notes'),
                    'sequence': int(idx+1)
                })
                if 'identity' in psg:
                    psg_vals.update({
                        'passport_number': psg['identity'].get('identity_number'),
                        'passport_expdate': psg['identity'].get('identity_expdate')
                    })
                to_psg_obj = to_psg_env.create(psg_vals)
                to_psg_obj.action_sync_handling()

                to_req_list = []

                if 'required' in psg:
                    for req in psg['required']:  # pricelist_obj.requirement_ids
                        req_vals = {
                            'to_passenger_id': to_psg_obj.id,
                            'requirement_id': self.env['tt.reservation.visa.requirements'].search(
                                [('reference_code', '=', req['id'])], limit=1).id,
                            'is_ori': req['is_original'],
                            'is_copy': req['is_copy'],
                            'check_uid': context['co_uid'],
                            'check_date': datetime.now()
                        }
                        to_req_obj = to_req_env.create(req_vals)
                        to_req_list.append(to_req_obj.id)  # akan dipindah ke edit requirements

                if 'handling' in psg:
                    for req in psg['handling']:
                        for handling in to_psg_obj.handling_ids:
                            if handling.handling_id.id == req['id']:
                                handling.write({
                                    'answer': req['answer']
                                })

                to_psg_obj.write({
                    'to_requirement_ids': [(6, 0, to_req_list)]
                })

                to_psg_list.append(to_psg_obj.id)
            res = Response().get_no_error(to_psg_list)
            return res
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Visa : ' + str(e))
            _logger.error(traceback.format_exc())
            return ERR.get_error(1004, additional_message='Error create Passenger Visa. There\'s something wrong.')

    def get_list_of_provider_visa(self):
        provider_list = []
        for rec in self.provider_booking_ids:
            if rec.provider_id:
                provider_list.append(rec.provider_id.name)
        self.provider_name = ', '.join(provider_list)

    def action_booked_visa(self, api_context=None):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        vals = {}
        if self.name == 'New':
            vals.update({
                'state': 'partial_booked',
            })

        vals.update({
            'state': 'booked',
            'booked_uid': api_context and api_context['co_uid'],
            'booked_date': datetime.now(),
        })

        self._compute_commercial_state()
        for pvdr in self.provider_booking_ids:
            pvdr.action_booked_api_visa(pvdr.to_dict(), api_context, self.hold_date)
        self.write(vals)

        try:
            if self.agent_type_id.is_send_email_booked:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_visa')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'visa',
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

    def action_issued_visa_api(self, data, context):
        book_obj = self.env['tt.reservation.visa'].search([('name', '=', data['order_number'])])

        if data.get('member'):
            customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', data['acquirer_seq_id'])]).id
        else:
            customer_parent_id = book_obj.agent_id.customer_parent_walkin_id.id

        vals = {}

        vals.update({
            'state': 'issued',
            'issued_uid': context['co_uid'],
            'issued_date': datetime.now(),
            'customer_parent_id': customer_parent_id
        })
        book_obj.write(vals)
        book_obj._compute_commercial_state()
        for rec in book_obj.provider_booking_ids:
            rec.write(vals)

        try:
            if self.agent_type_id.is_send_email_issued:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_visa')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'visa',
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

        return self.get_booking_visa_api(data, context)

    ######################################################################################################
    # PRINTOUT
    ######################################################################################################

    def do_print_out_visa_ho(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        visa_handling_ho_id = self.env.ref('tt_reservation_visa.action_report_printout_tt_visa_ho')
        if not self.printout_handling_ho_id:
            pdf_report = visa_handling_ho_id.report_action(self, data=data)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report.update({
                'ids': self.ids,
                'model': self._name,
            })
            pdf_report_bytes = visa_handling_ho_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Visa HO %s.pdf' % self.name,
                    'file_reference': 'Visa HO Handling',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': self.env.user.agent_id.id,
                    'co_uid': self.env.user.id,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_handling_ho_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_handling_ho_id.url,
        }
        return url
        # return self.env.ref('tt_reservation_visa.action_report_printout_tt_visa_ho').report_action(self, data=data)

    def do_print_out_visa_cust(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.visa'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        # data = {
        #     'ids': self.ids,
        #     'model': self._name,
        # }
        visa_handling_customer_id = book_obj.env.ref('tt_reservation_visa.action_report_printout_tt_visa_cust')
        if not book_obj.printout_handling_customer_id:
            pdf_report = visa_handling_customer_id.report_action(book_obj, data=data)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report.update({
                'ids': book_obj.ids,
                'model': book_obj._name,
            })
            pdf_report_bytes = visa_handling_customer_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Visa Customer %s.pdf' % book_obj.name,
                    'file_reference': 'Visa Customer Handling',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': book_obj.env.user.agent_id.id,
                    'co_uid': book_obj.env.user.id,
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.printout_handling_customer_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': book_obj.printout_handling_customer_id.url,
        }
        return url

    def print_itinerary(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.visa'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        visa_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_visa')

        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = visa_itinerary_id.report_action(book_obj, data=data)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report.update({
                'ids': book_obj.ids,
                'model': book_obj._name,
            })
            pdf_report_bytes = visa_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Itinerary Visa %s.pdf' % book_obj.name,
                    'file_reference': 'Itinerary Visa',
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

        book_obj = self.env['tt.reservation.visa'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        visa_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_visa')

        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = visa_itinerary_id.report_action(book_obj, data=data)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report.update({
                'ids': book_obj.ids,
                'model': book_obj._name,
            })
            pdf_report_bytes = visa_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Itinerary Visa %s (Price).pdf' % book_obj.name,
                    'file_reference': 'Itinerary Visa',
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
        visa_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_visa')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = visa_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = visa_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Visa HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Visa HO Invoice',
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
        # return visa_ho_invoice_id.report_action(self, data=datas)

    ######################################################################################################
    # OTHERS
    ######################################################################################################

    def action_booked_api_visa(self, context, pnr_list, hold_date):
        self.write({
            'state': 'booked',
            'pnr': ', '.join(pnr_list),
            'hold_date': hold_date,
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now()
        })

        try:
            if self.agent_type_id.is_send_email_booked:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_visa')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'visa',
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

    def check_provider_state(self, context, pnr_list=[], hold_date=False, req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            pass
            # self.calculate_service_charge()
            # self.action_booked_api_visa(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            #issued
            pass
            # issued
            ##get payment acquirer
            # if req.get('acquirer_seq_id'):
            #     acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', req['acquirer_seq_id'])])
            #     if not acquirer_id:
            #         raise RequestException(1017)
            # else:
            #     # raise RequestException(1017)
            #     acquirer_id = self.agent_id.default_acquirer_id
            #
            # if req.get('member'):
            #     customer_parent_id = acquirer_id.agent_id.id
            # else:
            #     customer_parent_id = self.agent_id.customer_parent_walkin_id.id
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            self.write({
                'state': 'refund',
                'state_visa': 'refund',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif all(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.action_reverse_visa(context)
        else:
            # entah status apa
            _logger.error('Entah status apa')
            raise RequestException(1006)

    def action_reverse_visa(self,context):
        self.write({
            'state': 'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    @api.multi
    @api.depends('passenger_ids')
    @api.onchange('passenger_ids')
    def _compute_immigration_consulate(self):
        for rec in self:
            if rec.passenger_ids:
                rec.immigration_consulate = rec.passenger_ids[0].pricelist_id.immigration_consulate

    def _compute_total_price(self):
        for rec in self:
            total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type == 'TOTAL':
                    total += sale.total
            rec.total_fare = total

    def _calc_grand_total(self):
        for rec in self:
            rec.total = 0
            rec.total_tax = 0
            rec.total_disc = 0
            # rec.total_commission = 0
            rec.total_fare = 0

            for line in rec.sale_service_charge_ids:
                if line.charge_type == 'TOTAL':
                    rec.total_fare += line.total
                if line.charge_type == 'tax':
                    rec.total_tax += line.total
                if line.charge_type == 'DISC':
                    rec.total_disc += line.total
                # if line.charge_type == 'ROC':
                #     rec.total_commission += line.total
                # if line.charge_type == 'RAC':
                #     rec.total_commission += line.total

            rec.total = rec.total_fare + rec.total_tax + rec.total_discount

    @api.depends("passenger_ids")
    def _compute_total_nta(self):
        for rec in self:
            nta_total = 0
            for psg in self.passenger_ids:
                nta_total += psg.pricelist_id.nta_price
            rec.total_nta = nta_total

    def randomizer_rec(self):
        import random
        list_agent_id = self.env['tt.agent'].sudo().search([]).ids
        country_id = self.env['res.country'].sudo().search([]).ids
        for rec in self.sudo().search([], limit=1000):
            new_rec = rec.sudo().copy()
            new_rec.update({
                'agent_id': list_agent_id[random.randrange(0, len(list_agent_id) - 1, 1)],
                'adult': random.randrange(0, 5, 1),
                'child': random.randrange(0, 5, 1),
                'infant': random.randrange(0, 5, 1),
                'country_id': country_id[random.randrange(0, len(country_id) - 1, 1)],
            })
        return True

    def get_aftersales_desc(self):
        desc_txt = ''
        for psg in self.passenger_ids:
            desc_txt += (psg.first_name if psg.first_name else '') + ' ' + \
                        (psg.last_name if psg.last_name else '') + ', ' + \
                        (psg.title if psg.title else '') + \
                        ' (' + (psg.passenger_type if psg.passenger_type else '') + ') ' + \
                        (psg.pricelist_id.entry_type.capitalize() if psg.pricelist_id.entry_type else '') + ' ' + \
                        (psg.pricelist_id.visa_type.capitalize() if psg.pricelist_id.visa_type else '') + ' ' + \
                        (psg.pricelist_id.process_type.capitalize() if psg.pricelist_id.process_type else '') + \
                        ' (' + str(psg.pricelist_id.duration if psg.pricelist_id.duration else '-') + ' days)' + '<br/>'
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
                for rec3 in rec2.passenger_ids.filtered(lambda x: x.passenger_id.id == rec.id):
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
                for rec3 in rec2.cost_service_charge_ids.filtered(lambda y: rec.id in y.passenger_visa_ids.ids):
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
                pax_pnr_data['parent_agent_commission'] = pax_pnr_data['total_commission'] - pax_pnr_data['agent_commission'] - pax_pnr_data['ho_commission']
                if pax_ticketed:
                    pax_data['pnr_list'].append(pax_pnr_data)
            pax_list.append(pax_data)
        return pax_list


class VisaSyncProductsChildren(models.TransientModel):
    _name = "visa.sync.product.children.wizard"
    _description = 'Visa Sync Product Children Wizard'

    def sync_data_to_children(self):
        try:
            visa_data_list = []
            data = self.env['tt.reservation.visa.pricelist'].get_inventory_api()
            if data['error_code'] == 0:
                for rec in data['response']:
                    detail_data = self.env['tt.reservation.visa.pricelist'].get_product_detail_api({'code': rec})
                    if detail_data['error_code'] == 0:
                        visa_data_list.append(detail_data['response'])
            gw_timeout = 10
            vals = {
                'provider_type': 'visa',
                'action': 'sync_products_to_children',
                'actions_todo': 'sync_products_to_children_visa',
                'data': visa_data_list,
                'timeout': gw_timeout
            }
            self.env['tt.api.webhook.data'].notify_subscriber(vals)
        except Exception as e:
            raise UserError(_('Failed to sync activity data to children!'))

    def product_sync_webhook_nosend(self, data, context):
        try:
            _logger.info("Receiving activity data from webhook...")
            data_vendor = self.env['tt.reservation.visa.pricelist'].search([('provider_id.code', '=', 'rodextrip_visa')])
            for rec in data_vendor:
                rec.active = False
            ho_obj = self.env['tt.agent'].search([('seq_id','=', data['ho_seq_id'])])
            for rec in data['data']:
                master_data = self.env['tt.reservation.visa.pricelist'].search([('reference_code', '=', rec['reference_code'] + '_rdx')], limit=1)
                if master_data:
                    data_update = {
                        'commercial_duration': rec['commercial_duration'],
                        'commission_price': rec['commission_price'],
                        'cost_price': rec['cost_price'],
                        'country_id': self.env['res.country'].search([('name', '=', rec['country_id'])]).id,
                        'currency_id': self.env['res.currency'].search([('name', '=', rec['currency_id'])]).id,
                        'delivery_nta_price': rec['delivery_nta_price'],
                        'description': rec['description'],
                        'duration': rec['duration'],
                        'entry_type': rec['entry_type'],
                        'immigration_consulate': rec['immigration_consulate'],
                        'name': rec['name'],
                        'notes': rec['notes'],
                        'nta_price': rec['nta_price'],
                        'pax_type': rec['pax_type'],
                        'process_type': rec['process_type'],
                        'reference_code': rec['reference_code'] + '_rdx',
                        'provider_id': self.env['tt.provider'].search([('code', '=', data['provider'])]).id,
                        'sale_price': rec['sale_price'],
                        'visa_nta_price': rec['visa_nta_price'],
                        'visa_type': rec['visa_type'],
                        'active': True,
                    }
                    if ho_obj.id not in master_data.ho_ids.ids:
                        data_update.update({
                            'ho_ids': [(4, ho_obj.id)]
                        })
                    master_data.update(data_update)
                    master_data.requirement_ids.unlink()
                    master_data.attachments_ids.unlink()
                    master_data.visa_location_ids.unlink()
                else:
                    master_data = self.env['tt.reservation.visa.pricelist'].create({
                        'commercial_duration': rec['commercial_duration'],
                        'commission_price': rec['commission_price'],
                        'cost_price': rec['cost_price'],
                        'country_id': self.env['res.country'].search([('name', '=', rec['country_id'])]).id,
                        'currency_id': self.env['res.currency'].search([('name', '=', rec['currency_id'])]).id,
                        'delivery_nta_price': rec['delivery_nta_price'],
                        'description': rec['description'],
                        'duration': rec['duration'],
                        'entry_type': rec['entry_type'],
                        'immigration_consulate': rec['immigration_consulate'],
                        'name': rec['name'],
                        'notes': rec['notes'],
                        'nta_price': rec['nta_price'],
                        'pax_type': rec['pax_type'],
                        'process_type': rec['process_type'],
                        'reference_code': rec['reference_code'] + '_rdx',
                        'provider_id': self.env['tt.provider'].search([('code', '=', data['provider'])], limit=1).id,
                        'sale_price': rec['sale_price'],
                        'visa_nta_price': rec['visa_nta_price'],
                        'visa_type': rec['visa_type'],
                        'active': True,
                        'ho_ids': [(4, ho_obj.id)]
                    })
                for data_requirement in rec['requirement_ids']:
                    self.env['tt.reservation.visa.requirements'].create({
                        'pricelist_id': master_data.id,
                        'name': data_requirement['name'],
                        'reference_code': data_requirement['reference_code'] + '_rdx',
                        'type_id': self.env['tt.traveldoc.type'].create(data_requirement['type_id']).id
                    })
                upload = self.env['tt.upload.center.wizard']
                co_agent_id = self.env.user.agent_id.id
                co_uid = self.env.user.id
                context = {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
                }
                attachments = []
                for data_attachment in rec['attachments_ids']:
                    try:
                        data_attachment['file'] = self.env['visa.sync.product.wizard'].url_to_base64(data['url'])
                        # data['filename'], data['file_reference'], data['file']
                        # KASIH TRY EXCEPT
                        upload = upload.upload_file_api(data_attachment, context)
                        attachments.append(self.env['tt.upload.center'].search([('seq_id', '=', upload['response']['seq_id'])], limit=1).id)
                #     pass
                #     #tt upload center
                #     self.env['tt.upload.center'].create({
                #         'pricelist_id': master_data.id,
                #     })
                    except Exception as e:
                        _logger.error("%s, %s" % (str(e), traceback.format_exc()))
                if attachments:
                    master_data.update({
                        'attachments_ids': [(6, 0, attachments)]
                    })
                for data_visa_location in rec['visa_location_ids']:
                    self.env['tt.master.visa.locations'].create({
                        'pricelist_id': master_data.id,
                        'name': data_visa_location['name'],
                        'location_type': data_visa_location['location_type'],
                        'address': data_visa_location['address'],
                        'city': data_visa_location['city']
                    })
            response = {
                'success': True
            }
            return ERR.get_no_error(response)

        except Exception as e:
            _logger.error(traceback.format_exc())
        return ERR.get_error()
