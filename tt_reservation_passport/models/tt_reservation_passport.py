from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging
import traceback
import copy
import json
import base64
from datetime import date
from ...tools.api import Response
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException

_logger = logging.getLogger(__name__)


STATE_PASSPORT = [
    ('draft', 'Request'),
    ('confirm', 'Confirm to HO'),
    ('partial_validate', 'Partial Validate'),
    ('validate', 'Validated by HO'),
    ('to_vendor', 'Send to Vendor'),
    ('vendor_process', 'Proceed by Vendor'),
    ('cancel', 'Canceled'),
    ('in_process', 'In Process'),
    ('payment', 'Payment'),
    ('refund', 'Refund'),
    ('process_by_consulate', 'Process by Consulate'),
    ('partial_proceed', 'Partial Proceed'),
    ('proceed', 'Proceed'),
    ('partial_approve', 'Partial Approve'),
    ('approve', 'Approve'),
    ('delivered', 'Delivered'),
    ('ready', 'Ready'),
    ('done', 'Done'),
    ('expired', 'Expired')
]


class TtPassport(models.Model):
    _name = 'tt.reservation.passport'
    _inherit = 'tt.reservation'
    _order = 'name desc'
    _description = 'Rodex Model'

    provider_type_id = fields.Many2one('tt.provider.type', string='Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_passport.tt_provider_type_passport'))

    description = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 default=lambda self: self.default_country_id())
    duration = fields.Char('Duration', readonly=True, states={'draft': [('readonly', False)]})
    total_cost_price = fields.Monetary('Total Cost Price', default=0, readonly=True)

    state_passport = fields.Selection(STATE_PASSPORT, 'State', default='draft', help='''draft = requested
                                            confirm = HO accepted
                                            validate = if all required documents submitted and documents in progress
                                            cancel = request cancelled
                                            in_process = before payment
                                            payment = payment
                                            partial proceed = partial proceed by consulate/immigration
                                            proceed = proceed by consulate/immigration
                                            delivered = Documents sent to agent
                                            ready = Documents ready at agent
                                            done = Documents given to customer''')

    ho_profit = fields.Monetary('HO Profit')

    estimate_date = fields.Date('Estimate Date', help='Estimate Process Done since the required documents submitted',
                                readonly=True)  # estimasi tanggal selesainya paspor
    payment_date = fields.Date('Payment Date', help='Date when accounting must pay the vendor')
    use_vendor = fields.Boolean('Use Vendor', readonly=True, default=False)
    vendor = fields.Char('Vendor Name')
    receipt_number = fields.Char('Reference Number')
    vendor_ids = fields.One2many('tt.reservation.passport.vendor.lines', 'passport_id', 'Expenses')

    document_to_ho_date = fields.Datetime('Document to HO Date', readonly=1)
    ho_validate_date = fields.Datetime('HO Validate Date', readonly=1)

    passenger_ids = fields.One2many('tt.reservation.passport.order.passengers', 'passport_id',
                                    'Passport Order Passengers', readonly=0)
    commercial_state = fields.Char('Payment Status', readonly=1, compute='_compute_commercial_state')  #
    confirmed_date = fields.Datetime('Confirmed Date', readonly=1)
    confirmed_uid = fields.Many2one('res.users', 'Confirmed By', readonly=1)

    validate_date = fields.Datetime('Validate Date', readonly=1)
    validate_uid = fields.Many2one('res.users', 'Validate By', readonly=1)
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'passport_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.provider.passport', 'booking_id', string='Provider Booking')  # , readonly=True, states={'cancel2': [('readonly', False)]}

    done_date = fields.Datetime('Done Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)

    recipient_name = fields.Char('Recipient Name')
    recipient_address = fields.Char('Recipient Address')
    recipient_phone = fields.Char('Recipient Phone')

    # to_vendor_date = fields.Datetime('Send To Vendor Date', readonly=1)
    # vendor_process_date = fields.Datetime('Vendor Process Date', readonly=1)
    in_process_date = fields.Datetime('In Process Date', readonly=1)
    delivered_date = fields.Datetime('Delivered Date', readonly=1)

    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)

    acquirer_id = fields.Char('Payment Method', readonly=True)  # dipake di agent invoice

    immigration_consulate = fields.Char('Immigration Consulate', readonly=1, compute="_compute_immigration_consulate")

    agent_commission = fields.Monetary('Agent Commission', default=0, compute="_compute_agent_commission")

    printout_handling_ho_id = fields.Many2one('tt.upload.center', readonly=True)
    printout_handling_customer_id = fields.Many2one('tt.upload.center', readonly=True)
    printout_itinerary_passport = fields.Many2one('tt.upload.center', 'Printout Itinerary', readonly=True)

    adjustment_ids = fields.One2many('tt.adjustment', 'res_id', 'Adjustment', readonly=True,
                                     domain=[('res_model', '=', 'tt_reservation_passport')])

    can_refund = fields.Boolean('Can Refund', default=False, readonly=True)

    ######################################################################################################
    # STATE
    ######################################################################################################

    # Jika pax belum menentukan tujuan negara, default country di isi singapore
    def default_country_id(self):
        return self.env['res.country'].search([('name', '=', 'Singapore')], limit=1).id

    @api.multi
    def _compute_commercial_state(self):
        for rec in self:
            if rec.state == 'issued':
                rec.commercial_state = 'Paid'
            else:
                rec.commercial_state = 'Unpaid'

    def action_fail_booked_passport(self):
        self.write({
            'state_passport': 'fail_booked',
            'state': 'fail_booked'
        })
        for psg in self.passenger_ids:
            psg.action_fail_booked()
        for pvdr in self.provider_booking_ids:
            pvdr.action_fail_booked_passport()
        self.message_post(body='Order FAILED (Booked)')

    def action_draft_passport(self):
        self.write({
            'state_passport': 'draft',
            'state': 'issued'
        })
        # saat mengubah state ke draft, akan mengubah semua state passenger ke draft
        for rec in self.passenger_ids:
            rec.action_draft()
        for rec in self.provider_booking_ids:
            rec.action_booked()
        self.message_post(body='Order DRAFT')

    def action_confirm_passport(self):
        is_confirmed = True
        for rec in self.passenger_ids:
            if rec.state not in ['confirm', 'cancel', 'validate']:
                is_confirmed = False

        if not is_confirmed:
            raise UserError(
                _('You have to Confirmed all The passengers document first.'))

        self.write({
            'state_passport': 'confirm',
            'state': 'booked',
            'confirmed_date': datetime.now(),
            'confirmed_uid': self.env.user.id
        })
        self.message_post(body='Order CONFIRMED')

    def action_partial_validate_passport(self):
        self.write({
            'state_passport': 'partial_validate'
        })
        self.message_post(body='Order PROCEED')

    def action_validate_passport(self):
        is_validated = True
        for rec in self.passenger_ids:
            if rec.state not in ['validate', 'cancel']:
                is_validated = False

        if not is_validated:
            raise UserError(
                _('You have to Validated all The passengers document first.'))

        self.write({
            'state_passport': 'validate',
            'validate_date': datetime.now(),
            'validate_uid': self.env.user.id
        })
        self.message_post(body='Order VALIDATED')

    def action_in_process_passport(self):
        data = {
            'order_number': self.name,
            'voucher': {
                'voucher_reference': self.voucher_code,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'provider_type': 'passport',
                'provider': self.provider_name,
            },
            'member': self.is_member,
            'acquirer_seq_id': self.payment_method
        }
        if self.voucher_code:
            data.update({
                'voucher': {
                    'voucher_reference': self.voucher_code,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'provider_type': 'passport',
                    'provider': self.provider_name,
                },
            })
        context = {
            'co_agent_type_id': self.agent_type_id.id,
            'co_agent_id': self.agent_id.id,
            'co_uid': self.booked_uid.id
        }

        payment_res = self.payment_reservation_api('passport', data, context)  # visa, member, payment_seq_id
        if payment_res['error_code'] != 0:
            raise UserError(payment_res['error_msg'])
        self.write({
            'state_passport': 'in_process',
            'in_process_date': datetime.now()
        })

        for rec in self.passenger_ids:
            if rec.state in ['validate', 'cancel']:
                rec.action_in_process()
        # self.action_booked_passport(context)
        self.action_issued_passport_api(data, context)
        provider_id = self.provider_booking_ids[0]
        expenses_vals = {
            'provider_id': provider_id.id,
            'passport_id': self.id,
            'reference_number': 'NTA',
            'nta_amount': self.total_nta,
        }
        provider_id.write({
            'vendor_ids': [(0, 0, expenses_vals)]
        })
        self.message_post(body='Order IN PROCESS')

    def action_payment_passport(self):
        self.write({
            'state_passport': 'payment'
        })
        self.message_post(body='Order PAYMENT')

    def action_in_process_immigration_passport(self):
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
            'state_passport': 'in_process',
            'can_refund': False,
            'in_process_date': datetime.now(),
            'estimate_date': date.today() + timedelta(days=estimate_days)
        })
        self.message_post(body='Order IN PROCESS TO IMMIGRATION')
        for rec in self.passenger_ids:
            rec.action_in_process2()

    def action_partial_proceed_passport(self):
        self.write({
            'state_passport': 'partial_proceed'
        })
        self.message_post(body='Order PARTIAL PROCEED')

    def action_proceed_passport(self):
        self.write({
            'state_passport': 'proceed'
        })
        self.message_post(body='Order PROCEED')

    def action_approved_passport(self):
        self.write({
            'state_passport': 'approve'
        })
        self.message_post(body='Order APPROVED')

    def action_partial_approved_passport(self):
        self.write({
            'state_passport': 'partial_approve'
        })
        self.message_post(body='Order PARTIAL APPROVED')

    def action_rejected_passport(self):
        self.write({
            'state_passport': 'reject'
        })
        self.message_post(body='Order REJECTED')

    def action_delivered_passport(self):
        """ Expenses wajib di isi untuk mencatat pengeluaran HO """
        for provider in self.provider_booking_ids:
            if not provider.vendor_ids:
                raise UserError(
                    _('You have to Fill Expenses.'))
        # if self.state_passport != 'delivered':
        #     self.calc_passport_vendor()
        self.write({
            'state_passport': 'delivered',
            'delivered_date': datetime.now()
        })
        self.message_post(body='Order DELIVERED')

    def action_cancel_passport(self):
        # set semua state passenger ke cancel
        if self.state_passport in ['in_process', 'payment']:
            self.can_refund = True
        # if self.state_passport not in ['in_process', 'partial_proceed', 'proceed', 'delivered', 'ready', 'done']:
        #     if self.sale_service_charge_ids:
        #         self._create_anti_ho_ledger_passport()
        #         self._create_anti_ledger_passport()
        #         self._create_anti_commission_ledger_passport()
        for rec in self.passenger_ids:
            rec.action_cancel()
        for rec in self.provider_booking_ids:
            rec.action_cancel()
        for rec3 in self.vendor_ids:
            rec3.sudo().unlink()
        self.write({
            'state_passport': 'cancel',
            'state': 'cancel',
        })
        self.message_post(body='Order CANCELED')

    def action_ready_passport(self):
        self.write({
            'state_passport': 'ready',
            'ready_date': datetime.now()
        })
        self.message_post(body='Order READY')

    def action_done_passport(self):
        self.write({
            'state_passport': 'done',
            'done_date': datetime.now()
        })
        self.message_post(body='Order DONE')

    def action_expired(self):
        super(TtPassport, self).action_expired()
        self.state_passport = 'expired'

    def calc_passport_upsell_vendor(self):
        diff_nta_upsell = 0
        total_charge = 0
        for provider in self.provider_booking_ids:
            for rec in provider.vendor_ids:
                if not rec.is_upsell_ledger_created and rec.amount != 0:
                    total_charge += rec.amount
                    diff_nta_upsell += (rec.amount - rec.nta_amount)
                    rec.is_upsell_ledger_created = True

        ledger = self.env['tt.ledger']
        if total_charge > 0:
            for rec in self:
                doc_type = []
                for sc in rec.sale_service_charge_ids:
                    if not sc.pricelist_id.passport_type in doc_type:
                        doc_type.append(sc.pricelist_id.passport_type)

                vals = ledger.prepare_vals(self._name, self.id, 'Additional Charge Passport : ' + rec.name, rec.name,
                                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 2,
                                           rec.currency_id.id, self.env.user.id, 0, total_charge,
                                           'Additional Charge Passport : ' + rec.name)
                vals.update({
                    'pnr': self.pnr,
                    'display_provider_name': self.provider_name,
                    'provider_type_id': self.provider_type_id.id
                })
                vals['agent_id'] = self.agent_id.id

                new_aml = ledger.create(vals)
                # new_aml.action_done()
                rec.ledger_id = new_aml

        """ Jika diff nta upsell > 0 """
        if diff_nta_upsell > 0:
            ledger = self.env['tt.ledger']
            for rec in self:
                doc_type = []
                for sc in rec.sale_service_charge_ids:
                    if not sc.pricelist_id.passport_type in doc_type:
                        doc_type.append(sc.pricelist_id.passport_type)

                vals = ledger.prepare_vals(self._name, self.id, 'NTA Upsell Passport : ' + rec.name, rec.name,
                                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 3,
                                           rec.currency_id.id, self.env.user.id, diff_nta_upsell, 0,
                                           'NTA Upsell passport : ' + rec.name)
                vals.update({
                    'pnr': self.pnr,
                    'display_provider_name': self.provider_name,
                    'provider_type_id': self.provider_type_id.id
                })
                vals['agent_id'] = rec.env.ref('tt_base.rodex_ho').id

                new_aml = ledger.create(vals)
                # new_aml.action_done()
                rec.ledger_id = new_aml
        elif diff_nta_upsell < 0:
            """ Jika diff nta upsell < 0 """
            ledger = self.env['tt.ledger']
            for rec in self:
                doc_type = []
                for sc in rec.sale_service_charge_ids:
                    if not sc.pricelist_id.passport_type in doc_type:
                        doc_type.append(sc.pricelist_id.passport_type)

                doc_type = ','.join(str(e) for e in doc_type)

                vals = ledger.prepare_vals(self._name, self.id, 'NTA Upsell Passport : ' + rec.name, rec.name,
                                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 3,
                                           rec.currency_id.id, self.env.user.id, 0, abs(diff_nta_upsell),
                                           'NTA Upsell Passport : ' + rec.name)
                vals.update({
                    'pnr': self.pnr,
                    'display_provider_name': self.provider_name,
                    'provider_type_id': self.provider_type_id.id
                })
                vals['agent_id'] = rec.env.ref('tt_base.rodex_ho').id

                new_aml = ledger.create(vals)
                # new_aml.action_done()
                rec.ledger_id = new_aml

    def calc_passport_vendor(self):
        """ Mencatat expenses ke dalam ledger passport """

        """ Hitung total expenses (pengeluaran) """
        total_expenses = 0
        for rec in self.vendor_ids:
            total_expenses += rec.amount

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
                    if not sc.pricelist_id.passport_type in doc_type:
                        doc_type.append(sc.pricelist_id.passport_type)

                doc_type = ','.join(str(e) for e in doc_type)

                vals = ledger.prepare_vals(self._name, self.id, 'Profit ' + doc_type + ' : ' + rec.name, rec.name,
                                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 3,
                                           rec.currency_id.id, self.env.user.id, ho_profit, 0)
                vals['agent_id'] = rec.env.ref('tt_base.rodex_ho').id

                new_aml = ledger.create(vals)
                # new_aml.action_done()
                rec.ledger_id = new_aml
        """ Jika profit HO < 0 (rugi) """
        if ho_profit < 0:
            ledger = self.env['tt.ledger']
            for rec in self:
                doc_type = []
                for sc in rec.sale_service_charge_ids:
                    if not sc.pricelist_id.passport_type in doc_type:
                        doc_type.append(sc.pricelist_id.passport_type)

                doc_type = ','.join(str(e) for e in doc_type)

                vals = ledger.prepare_vals(self._name, self.id, 'Additional Charge ' + doc_type + ' : ' + rec.name,
                                           rec.name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 3,
                                           rec.currency_id.id, self.env.user.id, 0, ho_profit)
                vals['agent_id'] = rec.env.ref('tt_base.rodex_ho').id

                new_aml = ledger.create(vals)
                # new_aml.action_done()
                rec.ledger_id = new_aml

    @api.one
    def action_issued_passport(self, data, api_context=None):
        """ Mengubah state menjadi issued / state passport menjadi in process """
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        if not api_context.get('co_uid'):
            api_context.update({
                'co_uid': self.env.user.id
            })

        vals = {}

        if self.name == 'New':
            vals.update({
                'state': 'partial_booked',
            })

        vals.update({
            'state': 'issued',
            'issued_uid': api_context['co_uid'],
            'issued_date': datetime.now(),
            'confirmed_uid': api_context['co_uid'],
            'confirmed_date': datetime.now(),
        })

        self.write(vals)

        self._compute_commercial_state()

    ######################################################################################################
    # PRINTOUT
    ######################################################################################################

    def do_print_out_passport_ho(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        passport_handling_ho_id = self.env.ref('tt_reservation_passport.action_report_printout_passport_ho')
        if not self.printout_handling_ho_id:
            pdf_report = passport_handling_ho_id.report_action(self, data=data)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report.update({
                'ids': self.ids,
                'model': self._name,
            })
            pdf_report_bytes = passport_handling_ho_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Passport HO %s.pdf' % self.name,
                    'file_reference': 'Passport HO Handling',
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
            'name': "ZZZ",
            'target': 'new',
            'url': self.printout_handling_ho_id.url,
        }
        return url
        # return passport_handling_ho_id.report_action(self, data=data)

    def do_print_out_passport_cust(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.passport'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        passport_handling_customer_id = self.env.ref('tt_reservation_passport.action_report_printout_passport_cust')
        if not book_obj.printout_handling_customer_id:
            pdf_report = passport_handling_customer_id.report_action(book_obj, data=data)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report.update({
                'ids': book_obj.ids,
                'model': book_obj._name,
            })
            pdf_report_bytes = passport_handling_customer_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Passport Customer %s.pdf' % book_obj.name,
                    'file_reference': 'Passport Customer Handling',
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
            'name': "ZZZ",
            'target': 'new',
            'url': self.printout_handling_ho_id.url,
        }
        return url
        # return passport_handling_customer_id.report_action(self, data=data)

    def print_itinerary(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.passport'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        passport_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_passport')

        if not book_obj.printout_itinerary_id:
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = passport_itinerary_id.report_action(book_obj, data=data)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report.update({
                'ids': book_obj.ids,
                'model': book_obj._name,
            })
            pdf_report_bytes = passport_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Itinerary Passport %s.pdf' % book_obj.name,
                    'file_reference': 'Itinerary Passport',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.printout_itinerary_passport = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "ZZZ",
            'target': 'new',
            'url': book_obj.printout_itinerary_passport.url,
        }
        return url
        # return passport_itinerary_id.report_action(book_obj, data=data)

    def print_ho_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        passport_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_passport')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = passport_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = passport_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Passport HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Passport HO Invoice',
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
            'name': "ZZZ",
            'target': 'new',
            'url': self.printout_ho_invoice_id.url,
        }
        return url
        # return passport_ho_invoice_id.report_action(self, data=datas)

    ######################################################################################################
    # CREATE
    ######################################################################################################

    param_sell_passport = {
        "search_data": [
            {
                "sequence": 0,
                "name": "Regular Passport (7 working days after photo)",
                "apply_type": "New",
                "type": {
                    "process_type": "Regular",
                    "duration": 7
                },
                "consulate": {
                    "city": "Surabaya",
                    "address": "IMIGRASI JUANDA , jalan Raya Juanda km 3-4 Surabaya"
                },
                "requirements": [],
                "attachments": [],
                "sale_price": {
                    "commission": 80000,
                    "total_price": 1310000,
                    "currency": "IDR"
                },
                "id": "passport_internal_Regular Passport (7 working days after photo)_1",
                "provider": "passport_internal",
                "notes": [],
                "commission": [
                    {
                        "charge_type": "RAC",
                        "charge_code": "rac",
                        "amount": -80000,
                        "currency": "IDR",
                        "commission_agent_id": 3
                    }
                ]
            },
            {
                "sequence": 1,
                "name": "Express Passport (5 working days after photo)",
                "apply_type": "New",
                "type": {
                    "process_type": "Express",
                    "duration": 5
                },
                "consulate": {
                    "city": "Surabaya",
                    "address": "IMIGRASI JUANDA , jalan Raya Juanda km 3-4 Surabaya"
                },
                "requirements": [],
                "attachments": [],
                "sale_price": {
                    "commission": 80000,
                    "total_price": 1460000,
                    "currency": "IDR"
                },
                "id": "passport_internal_Express Passport (5 working days after photo)_3",
                "provider": "passport_internal",
                "notes": [],
                "commission": [
                    {
                        "charge_type": "RAC",
                        "charge_code": "rac",
                        "amount": -80000,
                        "currency": "IDR",
                        "commission_agent_id": 3
                    }
                ]
            }
        ],
        "total_cost": 25,
        "provider": "passport_internal",
        "pax": {
            "adult": 1,
            "child": 0,
            "infant": 0,
            "elder": 0
        }
    }

    param_booker = {
        "title": "MR",
        "first_name": "Lala",
        "last_name": "Lala",
        "email": "asd@gmail.com",
        "calling_code": "62",
        "mobile": "81238823122",
        "nationality_name": "Indonesia",
        "booker_seq_id": "",
        "nationality_code": "ID",
        "gender": "male"
    }

    param_contact = [
        {
            "title": "MR",
            "first_name": "Lala",
            "last_name": "Lala",
            "email": "asd@gmail.com",
            "calling_code": "62",
            "mobile": "81238823122",
            "nationality_name": "Indonesia",
            "contact_seq_id": "",
            "is_booker": True,
            "nationality_code": "ID",
            "gender": "male"
        }
    ]

    param_passenger = [
        {
            "pax_type": "ADT",
            "first_name": "Lala",
            "last_name": "Lala",
            "title": "MR",
            "birth_date": "2003-01-31",
            "nationality_name": "Indonesia",
            "passenger_seq_id": "",
            "is_booker": False,
            "is_contact": False,
            "number": 1,
            "nationality_code": "ID",
            "master_passport_Id": "passport_internal_Regular Passport (7 working days after photo)_1",
            "required": [],
            "notes": "",
            "sequence": 1,
            "passenger_id": "PSG_1",
            "gender": "male",
            "is_also_booker": False,
            "is_also_contact": False
        },
        {
            "pax_type": "ADT",
            "first_name": "Testing",
            "last_name": "Lalala",
            "title": "MR",
            "birth_date": "2002-12-01",
            "nationality_name": "Indonesia",
            "passenger_seq_id": "CU.1204174",
            "is_booker": False,
            "is_contact": False,
            "number": 1,
            "nationality_code": "ID",
            "master_passport_Id": "passport_internal_Regular Passport (7 working days after photo)_1",
            "required": [],
            "notes": "",
            "sequence": 1,
            "passenger_id": "PSG_2",
            "gender": "male",
            "is_also_booker": False,
            "is_also_contact": False
        }
    ]

    param_context = {
        'co_uid': 8,
        'co_agent_id': 2,
        'co_agent_type_id': 2
    }

    param_search = {
        "passport_type": "Passport",
        "apply_type": "New",
        "immigration_consulate": "Surabaya",
        "provider": "passport_rodextrip"
    }

    param_payment = {
        "member": True,
        "acquirer_seq_id": "CTP.1900052",
        'force_issued': False
        # "seq_id": "PQR.9999999"
    }

    param_voucher = False

    def state_booking_passport_api(self, data, context):
        book_obj = self.env['tt.reservation.passport'].search([('name', '=', data.get('order_number'))], limit=1)
        if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1):
            if data['state'] == 'booked':
                book_obj.action_booked_passport(context)
            elif data['state'] == 'failed':
                book_obj.action_fail_booked_passport()

    def create_booking_passport_api(self, data, context):  #
        sell_passport = data['passport']  # self.param_sell_passport
        booker = data['booker']  # self.param_booker
        contact = data['contact']  # self.param_contact
        passengers = data['passenger']  # self.param_passenger
        payment = data['payment']  # self.param_payment
        search = data['payment']  # self.param_search
        context = context  # self.param_context
        voucher_ref = data['voucher']  # self.param_voucher

        try:
            header_val = {}
            booker_id = self.create_booker_api(booker, context)
            contact_id = self.create_contact_api(contact[0], booker_id, context)
            passenger_ids = self.create_customer_api(passengers, context, booker_id, contact_id)  # create passenger
            to_psg_ids = self._create_passport_order(passengers, passenger_ids)  # create visa order data['passenger']
            pricing = self.create_sale_service_charge_value(passengers, to_psg_ids, sell_passport)  # create pricing dict

            voucher = ''
            # if data['voucher']:
            #     voucher = data['voucher']['voucher_reference']

            header_val.update({
                'booker_id': booker_id.id,
                'voucher_code': voucher,
                'payment_method': payment['acquirer_seq_id'],
                'payment_active': True,
                'is_member': payment['member'],
                'contact_title': contact[0]['title'],
                'contact_id': contact_id.id,
                'contact_name': contact[0]['first_name'] + ' ' + contact[0]['last_name'],
                'contact_email': contact_id.email,
                'contact_phone': "%s - %s" % (
                    contact_id.phone_ids[0].calling_code, contact_id.phone_ids[0].calling_number),
                'passenger_ids': [(6, 0, to_psg_ids)],
                'adult': sell_passport['pax']['adult'],
                'child': sell_passport['pax']['child'],
                'infant': sell_passport['pax']['infant'],
                'state': 'booked',
                'agent_id': context['co_agent_id'],
                'user_id': context['co_uid'],
            })

            book_obj = self.sudo().create(header_val)

            for psg in book_obj.passenger_ids:
                for scs in psg.cost_service_charge_ids:
                    scs['description'] = book_obj.name

            book_obj.document_to_ho_date = datetime.now() + timedelta(days=1)
            book_obj.ho_validate_date = datetime.now() + timedelta(days=3)
            book_obj.hold_date = datetime.now() + timedelta(days=31)

            book_obj.pnr = book_obj.name

            book_obj.write({
                'state_passport': 'confirm',
                'confirmed_date': datetime.now(),
                'confirmed_uid': context['co_uid']
            })
            book_obj.message_post(body='Order CONFIRMED')

            self._calc_grand_total()

            country_obj = self.env['res.country']
            provider_obj = self.env['tt.provider']

            provider = provider_obj.env['tt.provider'].search([('code', '=', sell_passport['provider'])], limit=1)
            # country = country_obj.search([('name', '=', search['destination'])], limit=1)

            vals = {
                'booking_id': book_obj.id,
                'pnr': book_obj.name,
                'provider_id': provider.id,
                # 'country_id': country.id,
            }
            provider_passport_obj = book_obj.env['tt.provider.passport'].sudo().create(vals)

            book_obj.get_list_of_provider_passport()

            for psg in book_obj.passenger_ids:
                vals = {
                    'provider_id': provider_passport_obj.id,
                    'passenger_id': psg.id,
                    'pax_type': psg.passenger_type,
                    'pricelist_id': psg.pricelist_id.id
                }
                self.env['tt.provider.passport.passengers'].sudo().create(vals)

            provider_passport_obj.delete_service_charge()
            provider_passport_obj.create_service_charge(pricing)
            book_obj.calculate_service_charge()

            book_obj.action_booked_passport(context)

            response = {
                'order_number': book_obj.name
            }
            res = ''
            # res = self.get_booking_passport_api(response, context)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            res = Response().get_error(str(e), 500)
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
        return res

    # to generate sale service charge
    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        for provider in self.provider_booking_ids:
            sc_value = {}
            for p_sc in provider.cost_service_charge_ids:
                p_charge_code = p_sc.charge_code  # get charge code
                p_charge_type = p_sc.charge_type  # get charge type
                p_pax_type = p_sc.pax_type  # get pax type
                p_pricelist_id = p_sc.passport_pricelist_id.id
                if not sc_value.get(p_pricelist_id):  # if sc_value[pax type] not exists
                    sc_value[p_pricelist_id] = {}
                if p_charge_type != 'RAC':  # if charge type != RAC
                    if not sc_value[p_pricelist_id].get(p_charge_type):  # if charge type not exists
                        sc_value[p_pricelist_id][p_charge_type] = {}
                        sc_value[p_pricelist_id][p_charge_type].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0
                        })
                    c_type = p_charge_type
                    c_code = p_charge_type.lower()
                elif p_charge_type == 'RAC':  # elif charge type == RAC
                    if not sc_value[p_pricelist_id].get(p_charge_code):
                        sc_value[p_pricelist_id][p_charge_code] = {}
                        sc_value[p_pricelist_id][p_charge_code].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0
                        })
                    c_type = p_charge_code
                    c_code = p_charge_code
                sc_value[p_pricelist_id][c_type].update({
                    'charge_type': p_charge_type,
                    'charge_code': p_charge_code,
                    'pax_type': p_pax_type,
                    'pax_count': p_sc.pax_count,
                    'currency_id': p_sc.currency_id.id,
                    'foreign_currency_id': p_sc.foreign_currency_id.id,
                    'amount': sc_value[p_pricelist_id][c_type]['amount'] + p_sc.amount,
                    'total': sc_value[p_pricelist_id][c_type]['total'] + p_sc.total,
                    'foreign_amount': sc_value[p_pricelist_id][c_type]['foreign_amount'] + p_sc.foreign_amount,
                })

            values = []
            for p_pricelist, p_val in sc_value.items():
                for c_type, c_val in p_val.items():
                    curr_dict = {
                        'passport_pricelist_id': p_pricelist,
                        'booking_visa_id': self.id,
                        'description': provider.pnr
                    }
                    curr_dict.update(c_val)
                    values.append((0, 0, curr_dict))

            self.write({
                'sale_service_charge_ids': values
            })

    def create_sale_service_charge_value(self, passenger, passenger_ids, sell_passport):
        ssc_list = []
        ssc_list_final = []
        pricelist_env = self.env['tt.reservation.passport.pricelist'].sudo()
        passenger_env = self.env['tt.reservation.passport.order.passengers']
        for idx, psg in enumerate(passenger):
            ssc = []
            pricelist_id = self.env['tt.reservation.passport.pricelist'].search([('reference_code', '=', psg['master_passport_Id'])]).id
            pricelist_obj = pricelist_env.browse(pricelist_id)
            passenger_obj = passenger_env.browse(passenger_ids[idx])
            vals = {
                'amount': pricelist_obj.sale_price,
                'charge_code': 'fare',
                'charge_type': 'TOTAL',
                'passenger_passport_id': passenger_ids[idx],
                'description': pricelist_obj.description,
                'pax_type': 'ADT',
                'currency_id': pricelist_obj.currency_id.id,
                'pax_count': 1,
                'total': pricelist_obj.sale_price,
                'passport_pricelist_id': pricelist_obj.id,
                'sequence': passenger_obj.sequence
            }
            ssc_list.append(vals)
            # passenger_env.search([('id', '=', 'passenger_ids[idx])].limit=1).cost_service_charge_ids.create(ssc_list))
            ssc_obj = passenger_obj.cost_service_charge_ids.create(vals)
            ssc_obj.write({
                'passenger_passport_ids': [(6, 0, passenger_obj.ids)]
            })
            ssc.append(ssc_obj.id)

            commission_list2 = []
            for sell in sell_passport['search_data']:
                if str(sell['id']) == psg['master_passport_Id']:
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
                    ssc_obj2 = passenger_obj.cost_service_charge_ids.create(vals2)
                    ssc_obj2.write({
                        'passenger_passport_ids': [(6, 0, passenger_obj.ids)]
                    })
                    ssc.append(ssc_obj2.id)

            vals_fixed = {
                'commission_agent_id': self.env.ref('tt_base.rodex_ho').id,
                'amount': -(pricelist_obj.cost_price - pricelist_obj.nta_price),
                'charge_code': 'fixed',
                'charge_type': 'RAC',
                'passenger_passport_id': passenger_ids[idx],
                'description': pricelist_obj.description,
                'pax_type': 'ADT',
                'currency_id': pricelist_obj.currency_id.id,
                'pax_count': 1,
                'total': -(pricelist_obj.cost_price - pricelist_obj.nta_price),
                'passport_pricelist_id': pricelist_id,
                'sequence': passenger_obj.sequence,
                # 'passenger_visa_ids': []
            }
            ssc_list.append(vals_fixed)
            ssc_obj3 = passenger_obj.cost_service_charge_ids.create(vals_fixed)
            ssc_obj3.write({
                'passenger_passport_ids': [(6, 0, passenger_obj.ids)]
            })
            ssc.append(ssc_obj3.id)

            passenger_obj.write({
                'cost_service_charge_ids': [(6, 0, ssc)]
            })

        for ssc in ssc_list:
            # compare with ssc_list
            ssc_same = False
            for ssc_final in ssc_list_final:
                if ssc['passport_pricelist_id'] == ssc_final['passport_pricelist_id']:
                    if ssc['charge_code'] == ssc_final['charge_code']:
                        if ssc['pax_type'] == ssc_final['pax_type']:
                            ssc_same = True
                            # update ssc_final
                            ssc_final['pax_count'] = ssc_final['pax_count'] + 1,
                            ssc_final['passenger_passport_ids'].append(ssc['passenger_passport_id'])
                            ssc_final['total'] += ssc.get('amount')
                            ssc_final['pax_count'] = ssc_final['pax_count'][0]
                            break
            if ssc_same is False:
                vals = {
                    'amount': ssc['amount'],
                    'charge_code': ssc['charge_code'],
                    'charge_type': ssc['charge_type'],
                    'description': ssc['description'],
                    'passenger_passport_ids': [],
                    'pax_type': ssc['pax_type'],
                    'currency_id': ssc['currency_id'],
                    'pax_count': 1,
                    'total': ssc['total'],
                    'passport_pricelist_id': ssc['passport_pricelist_id']
                }
                vals['passenger_passport_ids'].append(ssc['passenger_passport_id'])
                ssc_list_final.append(vals)
        print('Final : ' + str(ssc_list_final))
        return ssc_list_final

    def _create_sale_service_charge(self, ssc_vals):
        service_chg_obj = self.env['tt.service.charge']
        ssc_ids = []
        for ssc in ssc_vals:
            ssc['passenger_passport_ids'] = [(6, 0, ssc['passenger_passport_ids'])]
            ssc_obj = service_chg_obj.create(ssc)
            print(ssc_obj.read())
            ssc_ids.append(ssc_obj.id)
        return ssc_ids

    def _create_passport_order(self, passengers, passenger_ids):
        pricelist_env = self.env['tt.reservation.passport.pricelist'].sudo()
        to_psg_env = self.env['tt.reservation.passport.order.passengers'].sudo()
        to_req_env = self.env['tt.reservation.passport.order.requirements'].sudo()
        to_psg_list = []

        for idx, psg in enumerate(passengers):
            pricelist_id = self.env['tt.reservation.passport.pricelist'].search([('reference_code', '=', psg['master_passport_Id'])]).id
            pricelist_obj = pricelist_env.browse(pricelist_id)
            psg_vals = passenger_ids[idx][0].copy_to_passenger()
            psg_vals.update({
                'name': psg_vals['first_name'] + ' ' + psg_vals['last_name'],
                'customer_id': passenger_ids[idx][0].id,
                'title': psg['title'],
                'pricelist_id': pricelist_id,
                'passenger_type': psg['pax_type'],
                'notes': psg.get('notes'),
                # Pada state request, pax akan diberi expired date dg durasi tergantung dari paket visa yang diambil
                'expired_date': fields.Date.today() + timedelta(days=pricelist_obj.duration),
                'sequence': int(idx + 1)
            })
            to_psg_obj = to_psg_env.create(psg_vals)

            to_req_list = []

            if 'required' in psg:
                for req in psg['required']:  # pricelist_obj.requirement_ids
                    req_vals = {
                        'to_passenger_id': to_psg_obj.id,
                        'requirement_id': self.env['tt.reservation.passport.requirements'].search(
                            [('id', '=', req['id'])], limit=1).id,
                        'is_ori': req['is_original'],
                        'is_copy': req['is_copy'],
                        'check_uid': self.env.user.id,
                        'check_date': datetime.now()
                    }
                    to_req_obj = to_req_env.create(req_vals)
                    to_req_list.append(to_req_obj.id)  # akan dipindah ke edit requirements

            to_psg_list.append(to_psg_obj.id)
        return to_psg_list

    def get_list_of_provider_passport(self):
        provider_list = []
        for rec in self.provider_booking_ids:
            if rec.provider_id:
                provider_list.append(rec.provider_id.name)
        self.provider_name = ', '.join(provider_list)

    def action_booked_passport(self, api_context=None):
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
            pvdr.action_booked_api_passport(pvdr.to_dict(), api_context, self.hold_date)
        self.write(vals)

    def action_booked_api_passport(self, context, pnr_list, hold_date):
        self.write({
            'state': 'booked',
            'pnr': ', '.join(pnr_list),
            'hold_date': hold_date,
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now()
        })

    def action_issued_passport_api(self, data, context):
        book_obj = self.env['tt.reservation.passport'].search([('name', '=', data['order_number'])])

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

    ######################################################################################################
    # OTHERS
    ######################################################################################################

    def check_provider_state(self, context, pnr_list=[], hold_date=False, req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.calculate_service_charge()
            self.action_booked_api_passport(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            ##get payment acquirer
            if req.get('acquirer_seq_id'):
                acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', req['acquirer_seq_id'])])
                if not acquirer_id:
                    raise RequestException(1017)
            else:
                # raise RequestException(1017)
                acquirer_id = self.agent_id.default_acquirer_id

            if req.get('member'):
                customer_parent_id = acquirer_id.agent_id.id
            else:
                customer_parent_id = self.agent_id.customer_parent_walkin_id.id

    @api.onchange('state')
    @api.depends('state')
    def _compute_expired_passport(self):
        for rec in self:
            if rec.state == 'expired':
                rec.state_passport = 'expired'

    @api.multi
    @api.depends('passenger_ids')
    def _compute_immigration_consulate(self):
        for rec in self:
            if rec.passenger_ids:
                rec.immigration_consulate = rec.passenger_ids[0].pricelist_id.immigration_consulate

    def _compute_agent_commission(self):
        for rec in self:
            agent_comm = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_code == 'rac':
                    agent_comm += sale.total
            rec.agent_commission = abs(agent_comm)

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
            rec.total_commission = 0
            rec.total_fare = 0

            for line in rec.sale_service_charge_ids:
                if line.charge_type == 'FARE':
                    rec.total_fare += line.total
                if line.charge_type == 'TAX':
                    rec.total_tax += line.total
                if line.charge_type == 'DISC':
                    rec.total_disc += line.total
                if line.charge_type == 'ROC':
                    rec.total_commission += line.total
                if line.charge_type == 'RAC':
                    rec.total_commission += line.total

            print('Total Fare : ' + str(rec.total_fare))
            rec.total = rec.total_fare + rec.total_tax + rec.total_disc
            rec.total_nta = rec.total - rec.total_commission

    @api.depends("passenger_ids")
    def _compute_total_nta(self):
        for rec in self:
            nta_total = 0
            for psg in self.passenger_ids:
                nta_total += psg.pricelist_id.nta_price
            rec.total_nta = nta_total

    def get_aftersales_desc(self):
        desc_txt = ''
        for psg in self.passenger_ids:
            desc_txt += psg.first_name + ' ' + psg.last_name + ', ' + psg.title + ' (' + psg.passenger_type + ') ' + \
                        psg.pricelist_id.apply_type.capitalize() + ' ' + psg.pricelist_id.passport_type.capitalize() \
                        + ' ' + psg.pricelist_id.process_type.capitalize() + ' (' + str(psg.pricelist_id.duration) + \
                        ' days)' + '<br/>'
        return desc_txt
