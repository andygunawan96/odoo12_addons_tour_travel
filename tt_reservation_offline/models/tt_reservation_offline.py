from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import traceback
import copy
import json
import base64
from ...tools.api import Response
from ...tools.ERR import RequestException
from ...tools import variables, ERR

_logger = logging.getLogger(__name__)

STATE_OFFLINE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('sent', 'Sent'),
    ('validate', 'Validate'),
    ('done', 'Done'),
    ('refund', 'Refund'),
    ('fail_refunded', 'Fail Refunded'),
    ('expired', 'Expired'),
    ('cancel', 'Canceled')
]

STATE_OFFLINE_STR = {
    'draft': 'Draft',
    'confirm': 'Confirm',
    'sent': 'Sent',
    'validate': 'Validate',
    'done': 'Done',
    'refund': 'Refund',
    'expired': 'Expired',
    'cancel': 'Canceled'
}

TYPE = [
    ('airline', 'Airlines'),
    ('train', 'Train'),
    ('hotel', 'Hotel'),
    ('cruise', 'Cruise'),
    ('merchandise', 'Merchandise'),
    ('rent_car', 'Rent Car'),  # kedepannya akan dihapus
    ('others', 'Other')
]

SECTOR_TYPE = [
    ('domestic', 'Domestic'),
    ('international', 'International')
]


class IssuedOffline(models.Model):
    _inherit = 'tt.reservation'
    _name = 'tt.reservation.offline'
    _order = 'name desc'
    _description = 'Rodex Model'

    # sub_agent_id = fields.Many2one('tt.agent', 'Sub-Agent', readonly=True, states={'draft': [('readonly', False)]},
    #                                help='COR / POR', related='booker_id.agent_id')

    # booking_id = fields.Many2one('tt.reservation.offline', 'Booking ID', default=lambda self: self.id)

    state = fields.Selection(variables.BOOKING_STATE, 'State', default='draft')
    state_offline = fields.Selection(STATE_OFFLINE, 'State Offline', default='draft')

    provider_type_id = fields.Many2one('tt.provider.type', string='Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_offline.tt_provider_type_offline'))
    offline_provider_type = fields.Selection(lambda self: self.get_offline_type(), 'Offline Provider Type')
    offline_provider_type_name = fields.Char('Additional Notes', readonly=False)
    provider_type_id_name = fields.Char('Transaction Name', readonly=True, compute='offline_type_to_char')
    provider_booking_ids = fields.One2many('tt.provider.offline', 'booking_id', string='Provider Booking')

    # carrier_id = fields.Many2one('tt.transport.carrier')
    sector_type = fields.Selection(SECTOR_TYPE, 'Sector', readonly=True, states={'draft': [('readonly', False)],
                                                                                 'pending': [('readonly', False)]})

    # 171121 CANDY: add field pnr, commission 80%, nta, nta 80%
    agent_commission = fields.Monetary('Agent Commission', readonly=True, compute='_get_agent_commission')
    parent_agent_commission = fields.Monetary('Parent Agent Commission', readonly=True, compute='_get_agent_commission')
    ho_commission = fields.Monetary('HO Commission', readonly=True, compute='_get_agent_commission')
    # states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    nta_price = fields.Monetary('NTA Price', readonly=True, compute='_get_nta_price', store=True)
    agent_nta_price = fields.Monetary('Agent Price', readonly=True, compute='_get_agent_price', store=True)

    resv_code = fields.Char('Vendor Order Number')

    # Date and UID
    confirm_date = fields.Datetime('Confirm Date', readonly=True, copy=False)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True, copy=False)
    sent_date = fields.Datetime('Sent Date', readonly=True, copy=False)
    sent_uid = fields.Many2one('res.users', 'Sent by', readonly=True, copy=False)
    validate_date = fields.Datetime('Validate Date', readonly=True, copy=False)
    validate_uid = fields.Many2one('res.users', 'Validate by', readonly=True, copy=False)
    done_date = fields.Datetime('Done Date', readonly=True, copy=False)
    done_uid = fields.Many2one('res.users', readonly=True, copy=False)
    cancel_date = fields.Datetime('Cancel Date', readonly=True, copy=False)
    cancel_uid = fields.Many2one('res.users', readonly=True, copy=False)

    # Monetary
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id,
                                  readonly=True, states={'draft': [('readonly', False)],
                                                         'pending': [('readonly', False)]})
    total = fields.Monetary('Total Sale Price', readonly=False, store=True, compute="")
    total_commission_amount = fields.Monetary('Total Commission Amount', store=True)
    # total_supplementary_price = fields.Monetary('Total Supplementary', compute='_get_total_supplement')

    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id,
                                 readonly=True)

    invoice_ids = fields.Many2many('tt.agent.invoice', 'issued_invoice_rel', 'issued_id', 'invoice_id', 'Invoice(s)')

    attachment_ids = fields.Many2many('tt.upload.center', 'offline_ir_attachments_rel', 'tt_issued_id',
                                      'attachment_id', string='Attachments')
    # passenger_qty = fields.Integer('Passenger Qty', default=1)
    cancel_message = fields.Text('Cancellation Messages', copy=False)
    cancel_can_edit = fields.Boolean('Can Edit Cancellation Messages')

    description = fields.Text('Description', help='Itinerary Description like promo code, how many night or other info',
                              readonly=True, states={'draft': [('readonly', False)],
                                                     'pending': [('readonly', False)]})

    line_ids = fields.One2many('tt.reservation.offline.lines', 'booking_id', 'Lines')
    passenger_ids = fields.One2many('tt.reservation.offline.passenger', 'booking_id', 'Passengers')

    incentive_amount = fields.Monetary('Insentif')
    vendor_amount = fields.Float('Vendor Amount')
    ho_final_amount = fields.Float('HO Amount', readonly=True, compute='compute_final_ho')
    ho_final_ledger_id = fields.Many2one('tt.ledger')

    # social_media_id = fields.Many2one('res.social.media.type', 'Order From(Media)', readonly=True,
    #                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    social_media_type = fields.Many2one('res.social.media.type', 'Order From(Media)')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_offline_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)],
                                                                     'pending': [('readonly', False)]})

    contact_ids = fields.One2many('tt.customer', 'reservation_offline_id', 'Contact Person', readonly=True,
                                  states={'draft': [('readonly', False)],
                                          'pending': [('readonly', False)]})
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True,
                                states={'draft': [('readonly', False)],
                                        'pending': [('readonly', False)]})
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True,
                                 states={'draft': [('readonly', False)],
                                         'pending': [('readonly', False)]}, domain="[('agent_id', '=', agent_id)]")
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True,
                                         states={'draft': [('readonly', False)],
                                                 'pending': [('readonly', False)]},
                                         help='COR / POR', domain="[('parent_agent_id', '=', agent_id)]")

    quick_validate = fields.Boolean('Quick Validate', default=False)

    acquirer_id = fields.Many2one('payment.acquirer', 'Payment Acquirer', readonly=True)

    split_from_resv_id = fields.Many2one('tt.reservation.offline', 'Splitted From', readonly=1)
    split_to_resv_ids = fields.One2many('tt.reservation.offline', 'split_from_resv_id', 'Splitted To', readonly=1)

    # display_mobile = fields.Char('Contact Person for Urgent Situation',
    #                              readonly=True, states={'draft': [('readonly', False)]})
    # refund_id = fields.Many2one('tt.refund', 'Refund')

    ####################################################################################################
    # REPORT
    ####################################################################################################

    @api.depends('offline_provider_type')
    def offline_type_to_char(self):
        for rec in self:
            if rec.offline_provider_type:
                rec.provider_type_id_name = rec.offline_provider_type
            else:
                rec.provider_type_id_name = ''

    # @api.depends('offline_provider_type')
    # def offline_type_to_char2(self):
    #     if self.offline_provider_type != 'other':
    #         self.offline_provider_type_name = self.offline_provider_type

    def get_offline_type(self):
        provider_type_list = []
        for rec in self.env['tt.provider.type'].get_provider_type():
            if rec != 'offline':
                provider_type_list.append((rec, rec.capitalize()))
        provider_type_list.append(('other', 'Other'))
        return provider_type_list

    def print_invoice_ticket(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'provider_type': self.provider_type_id_name
        }
        if self.provider_type_id_name == 'airline':
            return self.env.ref('tt_reservation_offline.action_report_printout_invoice_ticket_airline').report_action(self, data=data)
        else:
            return self.env.ref('tt_reservation_offline.action_report_printout_invoice_ticket').report_action(self, data=data)

    ####################################################################################################
    # STATE
    ####################################################################################################

    @api.one
    def action_confirm(self, kwargs={}):
        if not self.check_line_empty():
            if not self.check_passenger_empty():
                if self.total != 0:
                    self.state_offline = 'confirm'
                    self.state = 'draft'
                    self.confirm_date = fields.Datetime.now()
                    self.confirm_uid = kwargs.get('co_uid') and kwargs['co_uid'] or self.env.user.id
                    if not self.acquirer_id:
                        self.acquirer_id = self.agent_id.default_acquirer_id
                    if self.line_ids:
                        self.get_pnr_list()
                        self.get_carrier_name()
                    if self.offline_provider_type != 'other':
                        self.offline_provider_type_name = self.offline_provider_type
                    # self.send_push_notif()
                else:
                    raise UserError(_('Sale Price can\'t be 0 (Zero)'))
            else:
                raise UserError(_('Passenger(s) can\'t be 0 (Zero)'))
        else:
            raise UserError(_('Line(s) can\'t be empty'))

    @api.one
    def action_cancel(self):
        if self.state_offline != 'done':
            if self.state_offline == 'validate':
                for rec in self.ledger_ids:
                    if not rec.is_reversed:
                        rec.reverse_ledger()
                    # ledger_obj.update({
                    #     'transaction_type': self.provider_type_id_name,
                    #     'description': rec.description
                    # })
            self.state = 'cancel'
            self.state_offline = 'cancel'
            self.cancel_date = fields.Datetime.now()
            self.cancel_uid = self.env.user.id
            return True

    @api.one
    def action_draft(self):
        self.state = 'draft'
        self.state_offline = 'draft'
        self.confirm_date = False
        self.confirm_uid = False
        self.sent_date = False
        self.sent_uid = False
        self.validate_date = False
        self.validate_uid = False
        self.issued_date = False
        self.issued_uid = False
        self.cancel_date = False
        self.cancel_uid = False
        self.cancel_message = False
        self.resv_code = False

    @api.one
    def action_validate(self, kwargs={}):
        # create prices
        self.state = 'booked'

        req = {
            'book_id': self.id,
            'order_number': self.name,
            'acquirer_seq_id': self.acquirer_id.seq_id,
            'member': False
        }
        if self.customer_parent_id.customer_parent_type_id.id != self.env.ref('tt_base.customer_type_fpo').id:
            req.update({
                'member': True,
                'acquirer_seq_id': self.customer_parent_id.seq_id
            })
        context = {
            'co_uid': self.env.user.id,
            'co_agent_id': self.agent_id.id
        }

        if self.state_offline == 'validate':
            raise UserError('State has already been validated. Please refresh the page.')
        if self.state_offline == 'done':
            raise UserError('State has already been done. Please refresh the page.')
        payment = self.payment_reservation_api('offline', req, context)
        if payment['error_code'] != 0:
            _logger.error(payment['error_msg'])
            raise UserError(_(payment['error_msg']))

        self.state_offline = 'validate'
        self.vendor_amount = self.nta_price
        self.compute_final_ho()
        self.issued_date = fields.Datetime.now()
        self.issued_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
        for provider in self.provider_booking_ids:
            provider.issued_date = self.issued_date
            provider.issued_uid = self.issued_uid
        try:
            self.env['tt.offline.api.con'].send_approve_notification(self.name, self.env.user.name,
                                                                     self.get_total_amount())
        except Exception as e:
            _logger.error("Send ISSUED OFFLINE Approve Notification Telegram Error")

    def check_pnr_empty(self):
        empty = False
        for rec in self.line_ids:
            if rec.pnr is False:
                empty = True
            else:
                if len(rec.pnr) <= 1:
                    empty = True
        return empty

    def check_provider_empty(self):
        empty = False
        for rec in self.line_ids:
            if not rec.provider_id or rec.provider_id.id is False:
                empty = True
        return empty

    @api.one
    def action_sent(self):
        if self.check_provider_empty() is False:
            if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                if self.check_pnr_empty():
                    raise UserError(_('PNR(s) can\'t be Empty'))
        else:
            raise UserError(_('Provider(s) can\'t be Empty'))
        print(self.issued_uid.id)
        if self.state_offline == 'validate':
            raise UserError(_('Offline has been validated. You cannot go back to Sent. Please refresh the page.'))
        if self.state_offline == 'done':
            raise UserError(_('Offline has been done. You cannot go back to Sent. Please refresh the page.'))
        self.state_offline = 'sent'
        self.sent_date = fields.Datetime.now()
        self.sent_uid = self.env.user.id
        self.create_provider_offline()
        for provider in self.provider_booking_ids:
            provider.state = 'booked'
            provider.confirm_date = self.confirm_date
            provider.confirm_uid = self.confirm_uid
            provider.sent_date = self.sent_date
            provider.sent_uid = self.sent_uid
        self.get_pnr_list_from_provider()
        self.get_provider_name()
        self.get_carrier_name()
        if not self.provider_name:
            raise UserError(_('List of Provider can\'t be Empty'))
        for idx, provider in enumerate(self.provider_booking_ids):
            # create pricing list
            if self.provider_type_id_name in ['hotel']:
                provider.create_service_charge_hotel(idx)
            else:
                provider.create_service_charge()
        self.calculate_service_charge()

    @api.one
    def action_issued_backend(self):
        is_enough = self.action_validate()
        if is_enough[0]['error_code'] != 0:
            raise UserError(is_enough[0]['error_msg'])

    @api.one
    def action_done(self,  kwargs={}):
        if self.state_offline != 'cancel':
            if self.resv_code:
                if self.provider_type_id_name in ['activity', 'hotel']:
                    if self.check_pnr_empty():
                        raise UserError(_('PNR(s) can\'t be Empty'))
                if self.attachment_ids:
                    self.state = 'issued'
                    self.state_offline = 'done'
                    self.done_date = fields.Datetime.now()
                    self.done_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
                    self.booked_date = fields.Datetime.now()
                    self.booked_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
                    if self.provider_type_id_name in ['activity', 'hotel']:
                        self.get_pnr_list()
                    else:
                        self.get_pnr_list_from_provider()
                    self.get_provider_name()
                    self.create_final_ho_ledger(self)
                    for provider in self.provider_booking_ids:
                        provider.state = 'issued'
                        provider.issued_date = self.issued_date
                        provider.issued_uid = self.issued_uid
                else:
                    raise UserError('Attach Booking/Resv. Document')
            else:
                raise UserError('Add Vendor Order Number')
        else:
            raise UserError('Canceled offline cannot be done.')

    def offline_set_to_issued(self):
        if self.state_offline != 'cancel':
            if self.provider_type_id_name in ['activity', 'hotel']:
                if self.check_pnr_empty():
                    raise UserError(_('PNR(s) can\'t be Empty'))
            self.state = 'issued'
            self.state_offline = 'done'
            self.done_date = fields.Datetime.now()
            self.done_uid = self.env.user.id
            self.booked_date = fields.Datetime.now()
            self.booked_uid = self.env.user.id
            for provider in self.provider_booking_ids:
                provider.state = 'issued'
                provider.issued_date = self.issued_date
                provider.issued_uid = self.issued_uid
        else:
            raise UserError('Canceled offline cannot be done.')

    @api.one
    def action_refund(self):
        self.write({
            'state': 'refund',
            'state_offline': 'refund',
            'refund_date': datetime.now(),
            'refund_uid': self.env.user.id
        })

    def action_expired(self):
        if self.state_offline == 'confirm' and self.hold_date < datetime.now():
            super(IssuedOffline, self).action_expired()  # Set state = expired
            self.state_offline = 'expired'  # Set state_offline = expired

    @api.one
    def action_quick_issued(self):
        if self.total > 0 and self.nta_price > 0:
            self.action_sent()
            self.action_validate()
        else:
            raise UserError(_('Sale Price or NTA Price can\'t be 0 (Zero)'))

    def validate_api(self, data, context):
        try:
            _logger.info("Get req\n" + json.dumps(context))
            book_obj = self.get_book_obj(data.get('book_id'), data.get('order_number'))
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)
            if book_obj.agent_id.id == context.get('co_agent_id', -1):
                book_obj.action_issued_backend()
            else:
                raise RequestException(1001)

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()

        except Exception as e:
            _logger.error(traceback.format_exc())
        return ERR.get_error(1013)

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
                if not sc_value.get(p_pax_type):
                    sc_value[p_pax_type] = {}
                if p_charge_type != 'RAC':
                    if not sc_value[p_pax_type].get(p_charge_type):
                        sc_value[p_pax_type][p_charge_type] = {}
                        sc_value[p_pax_type][p_charge_type].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0,
                            'pax_count': 0
                        })
                    c_type = p_charge_type
                    c_code = p_charge_type.lower()
                elif p_charge_type == 'RAC':
                    if not sc_value[p_pax_type].get(p_charge_code):
                        sc_value[p_pax_type][p_charge_code] = {}
                        sc_value[p_pax_type][p_charge_code].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0,
                            'pax_count': 0
                        })
                    c_type = p_charge_code
                    c_code = p_charge_code
                sc_value[p_pax_type][c_type].update({
                    'charge_type': p_charge_type,
                    'charge_code': c_code,
                    'pax_count': sc_value[p_pax_type][c_type]['pax_count'] + p_sc.pax_count,
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
                    curr_dict['booking_offline_id'] = self.id
                    curr_dict['description'] = provider.pnr
                    curr_dict.update(c_val)
                    values.append((0, 0, curr_dict))

            self.write({
                'sale_service_charge_ids': values
            })

    def sync_service_charge(self):
        for provider in self.provider_booking_ids:
            for scs in provider.cost_service_charge_ids:
                psg_list = []
                for psg in self.passenger_ids:
                    if scs.pax_type == psg.pax_type:
                        psg_list.append(psg.id)
                scs.passenger_offline_ids = [(6, 0, psg_list)]

    def sync_all_service_charge(self):
        book_objs = self.env['tt.reservation.offline'].search([('state_offline', 'in', ['sent', 'validate', 'done']),
                                                               ('offline_provider_type', 'not in', ['', 'hotel'])])
        for book in book_objs:
            book.sync_service_charge()

    def set_back_to_confirm(self):
        self.state = 'draft'
        self.state_offline = 'confirm'

    def create_final_ho_ledger(self, provider_obj):
        for rec in self:
            if rec.nta_price > rec.vendor_amount:
                # Agent Ledger
                pnr = self.get_pnr_list_from_provider()

                vals = self.env['tt.ledger'].prepare_vals(self._name, self.id, 'Resv : ' + rec.name, 'Profit&Loss: ' + rec.name,
                                                          rec.validate_date, 3, rec.currency_id.id, self.env.user.id,
                                                          rec.ho_final_amount, 0)
                vals = self.env['tt.ledger'].prepare_vals_for_resv(self, pnr, vals)
                vals.update({
                    'pnr': self.pnr,
                    'provider_type_id': self.provider_type_id.id,
                    'display_provider_name': self.provider_name,
                    'agent_id': self.env.ref('tt_base.rodex_ho').id
                })
                new_aml = rec.env['tt.ledger'].create(vals)
            else:
                # Agent Ledger
                pnr = self.get_pnr_list_from_provider()

                vals = self.env['tt.ledger'].prepare_vals(self._name, self.id, 'Resv : ' + rec.name,
                                                          'Profit&Loss: ' + rec.name,
                                                          rec.validate_date, 3, rec.currency_id.id, self.env.user.id,
                                                          0, abs(rec.ho_final_amount))
                vals = self.env['tt.ledger'].prepare_vals_for_resv(self, pnr, vals)
                vals.update({
                    'pnr': self.pnr,
                    'provider_type_id': self.provider_type_id.id,
                    'display_provider_name': self.provider_name,
                    'agent_id': self.env.ref('tt_base.rodex_ho').id
                })
                new_aml = rec.env['tt.ledger'].create(vals)

    def create_provider_offline(self):
        for provider in self.provider_booking_ids:
            provider.unlink()
        pnr_found = []
        for line in self.line_ids:
            if line.pnr not in pnr_found or self.provider_type_id_name in ['hotel', 'activity']:
                vals = {
                    'booking_id': self.id,
                    'provider_id': line.provider_id.id,
                    'pnr': line.pnr,
                    'confirm_uid': self.env.user.id,
                    'confirm_date': datetime.now()
                }
                self.env['tt.provider.offline'].create(vals)
                pnr_found.append(line.pnr)

    ####################################################################################################
    # Set, Get & Compute
    ####################################################################################################

    @api.onchange('total', 'total_commission_amount')
    @api.depends('total', 'total_commission_amount')
    def _get_nta_price(self):
        for rec in self:
            rec.nta_price = rec.total - rec.total_commission_amount  # - rec.incentive_amount

    @api.onchange('agent_commission')
    @api.depends('agent_commission', 'total')
    def _get_agent_price(self):
        for rec in self:
            rec.agent_nta_price = rec.total - rec.total_commission_amount + rec.parent_agent_commission + rec.ho_commission

    def get_display_provider_name(self):
        provider_list = []
        if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
            for rec in self.line_ids:
                found = False
                if rec.carrier_id.name in provider_list:
                    found = True
                if found is False:
                    provider_list.append(rec.carrier_id.name)
            providers = ''
            for rec in provider_list:
                if rec:
                    providers += rec
            return providers
        elif self.provider_type_id_name == 'hotel':
            for rec in self.line_ids:
                found = False
                if rec.hotel_name in provider_list:
                    found = True
                if found is False:
                    provider_list.append(rec.hotel_name)
            providers = ''
            for rec in provider_list:
                providers += rec
            return providers
        elif self.provider_type_id_name == 'activity':
            for rec in self.line_ids:
                found = False
                if rec.activity_name in provider_list:
                    found = True
                if found is False:
                    provider_list.append(rec.activity_name.name)
            providers = ''
            for rec in provider_list:
                providers += rec
            return providers
        else:
            return ''

    def get_fee_amount(self, agent_id, provider_type_id, input_commission, passenger_id=None):
        ho_agent = self.env.ref('tt_base.rodex_ho').sudo()

        pricing_obj = self.env['tt.pricing.agent'].sudo()

        price_obj = pricing_obj.sudo().search([('agent_type_id', '=', agent_id.agent_type_id.id),
                                               ('provider_type_id', '=', provider_type_id.id)], limit=1)

        """ kurangi input amount dengan fee amount. masukkan fee amount ke dalam service charge HOC """
        vals = {
            'commission_agent_id': ho_agent.id,
            'agent_id': ho_agent.id,
            'agent_name': ho_agent.name,
            'agent_type_id': ho_agent.agent_type_id.id,
            'amount': price_obj.fee_amount if price_obj.fee_amount < input_commission else input_commission,
            'total': price_obj.fee_amount if price_obj.fee_amount < input_commission else input_commission,
            'charge_type': 'RAC',
            'charge_code': 'hoc',
            'description': self.name,
            'pax_type': passenger_id.pax_type if passenger_id else 'ADT',
            'currency_id': price_obj.currency_id.id,
            'passenger_offline_ids': []
        }
        if passenger_id:
            vals['passenger_offline_ids'].append(passenger_id.id)
        return vals

    @api.onchange('total_commission_amount')
    @api.depends('total_commission_amount')
    def _get_agent_commission(self):
        for rec in self:
            if rec.offline_provider_type:
                pnr_list = []
                fee_amount_list = []
                total_fee_amount = 0
                total_amount = rec.total_commission_amount

                pricing_obj = rec.env['tt.pricing.agent'].sudo()

                """ Get provider type id """
                if rec.offline_provider_type != 'other':
                    provider_type_id = self.env['tt.provider.type'].sudo().search(
                        [('code', '=', rec.offline_provider_type)], limit=1)
                else:
                    provider_type_id = self.env['tt.provider.type'].sudo().search([('code', '=', 'offline')], limit=1)

                if not self.split_to_resv_ids:
                    """ hitung fee amount di sini """
                    for line in rec.line_ids:
                        if rec.offline_provider_type in ['airline', 'train']:
                            """ Jika offline type = airline, rule fee amount : per PNR per pax """
                            if line.pnr not in pnr_list:
                                pnr_list.append(line.pnr)
                                for psg in rec.passenger_ids:
                                    fee_amount_vals = rec.sudo().get_fee_amount(rec.agent_id, provider_type_id,
                                                                                rec.total_commission_amount, psg)
                                    fee_amount_list.append(fee_amount_vals)
                                    total_amount -= fee_amount_vals.get('amount')
                                    total_fee_amount += fee_amount_vals.get('amount')
                        elif rec.offline_provider_type == 'hotel':
                            """ Jika offline type = hotel, rule fee amount : per night per room * qty """
                            check_in = datetime.strptime(line.check_in, '%Y-%m-%d')
                            check_out = datetime.strptime(line.check_out, '%Y-%m-%d')
                            days = check_out - check_in
                            days_int = int(days.days)
                            for day in range(0, days_int):
                                fee_amount_vals = rec.get_fee_amount(rec.agent_id, provider_type_id,
                                                                     rec.total_commission_amount)
                                fee_amount_vals['amount'] = fee_amount_vals.get('amount') * line.obj_qty
                                fee_amount_vals['total'] = fee_amount_vals.get('total') * line.obj_qty
                                fee_amount_list.append(fee_amount_vals)
                                total_amount -= fee_amount_vals.get('total')
                                total_fee_amount += fee_amount_vals.get('total')
                        else:
                            """ else, rule fee amount : per line/provider per pax """
                            for psg in rec.passenger_ids:
                                fee_amount_vals = rec.get_fee_amount(rec.agent_id, provider_type_id,
                                                                     rec.total_commission_amount, psg)
                                fee_amount_list.append(fee_amount_vals)
                                total_amount -= fee_amount_vals.get('amount')
                                total_fee_amount += fee_amount_vals.get('amount')

                    rec.agent_commission = 0
                    rec.parent_agent_commission = 0
                    rec.ho_commission = 0

                    """ masukkan semua fee amount ke HO Commission """
                    if total_amount > 0:
                        rec.ho_commission += total_fee_amount
                    else:
                        rec.ho_commission += rec.total_commission_amount

                    if total_amount > 0:
                        """ Get commission list """
                        commission_list = pricing_obj.sudo().get_commission(total_amount, rec.agent_id, provider_type_id)

                        if rec.total_commission_amount != 0:
                            for comm in commission_list:
                                if comm.get('code') == 'rac':
                                    rec.agent_commission += comm.get('amount')
                                elif comm.get('agent_type_id') == rec.env.ref('tt_base.rodex_ho').sudo().agent_type_id.id:
                                    rec.ho_commission += comm.get('amount')
                                else:
                                    rec.parent_agent_commission += comm.get('amount')
                else:
                    commission_list = []
                    """ Jika belum di split, compute commission dari pricing di provider """
                    for provider in self.provider_booking_ids:
                        for scs in provider.cost_service_charge_ids:
                            scs_val = scs.to_dict()
                            if scs.charge_type != 'FARE':
                                scs_val['agent_type_id'] = scs.commission_agent_id.agent_type_id.id
                                commission_list.append(scs_val)

                    rec.agent_commission = 0
                    rec.parent_agent_commission = 0
                    rec.ho_commission = 0

                    for comm in commission_list:
                        if comm['charge_code'] == 'hoc':
                            rec.ho_commission += comm['amount']

                    total_amount -= rec.ho_commission
                    percentage_rem = 100

                    price_obj = pricing_obj.sudo().search([('agent_type_id', '=', rec.agent_id.agent_type_id.id),
                                                           ('provider_type_id', '=', provider_type_id.id)], limit=1)
                    if price_obj.basic_amount_type == 'percentage':
                        rec.agent_commission = total_amount / 100 * price_obj.basic_amount
                        percentage_rem -= price_obj.basic_amount
                    elif price_obj.basic_amount_type == 'amount':
                        rec.agent_commission = price_obj.basic_amount
                    for line in price_obj.line_ids:
                        if line.agent_type_id.id == self.env.ref('tt_base.rodex_ho').agent_type_id.id:
                            if line.basic_amount_type == 'percentage':
                                rec.ho_commission += total_amount / 100 * line.basic_amount
                                percentage_rem -= line.basic_amount
                            else:
                                rec.ho_commission += line.basic_amount
                        else:
                            if line.basic_amount_type == 'percentage':
                                rec.parent_agent_commission += total_amount / 100 * line.basic_amount
                                percentage_rem -= line.basic_amount
                            else:
                                rec.parent_agent_commission += line.basic_amount
                    if percentage_rem > 0 and price_obj.basic_amount_type == 'percentage':
                        rec.ho_commission += total_amount / 100 * percentage_rem

    # Hitung harga final / Agent NTA Price
    @api.onchange('vendor_amount', 'nta_price')
    def compute_final_ho(self):
        for rec in self:
            rec.ho_final_amount = rec.nta_price - rec.vendor_amount

    @api.onchange('contact_id')
    def _filter_customer_parent(self):
        if self.contact_id:
            return {'domain': {
                'customer_parent_id': [('customer_ids', 'in', self.contact_id.id)]
            }}

    def sync_all_carrier_list(self):
        book_objs = self.env['tt.reservation.offline'].search([('offline_provider_type', 'in', ['airline', 'train'])])
        for book in book_objs:
            book.get_carrier_name()

    def get_provider_name(self):
        provider_list = []
        for rec in self.line_ids:
            if rec.provider_id and rec.provider_name:
                if rec.provider_name not in provider_list:
                    provider_list.append(rec.provider_name)
        if len(provider_list) != 0:
            self.provider_name = ', '.join(provider_list)

    def get_carrier_name(self):
        carrier_list = []
        for rec in self.line_ids:
            if rec.carrier_id:
                if rec.carrier_id.name not in carrier_list:
                    carrier_list.append(rec.carrier_id.name)
        if len(carrier_list) != 0:
            self.carrier_name = ', '.join(carrier_list)

    def get_provider_name_from_provider(self):
        provider_list = []
        for rec in self.provider_booking_ids:
            if rec.provider_id:
                if rec.provider_id.name not in provider_list:
                    provider_list.append(rec.provider_id.name)
        self.provider_name = ', '.join(provider_list)

    def get_pnr_list(self):
        pnr_list = []
        for rec in self.line_ids:
            if rec.pnr:
                if rec.pnr not in pnr_list:
                    pnr_list.append(rec.pnr)
        self.pnr = ', '.join(pnr_list)

    def get_pnr_list_from_provider(self):
        pnr_list = []
        for rec in self.provider_booking_ids:
            if rec.pnr:
                if rec.pnr not in pnr_list:
                    pnr_list.append(rec.pnr)
        self.pnr = ', '.join(pnr_list)

    def check_line_empty(self):
        empty = True
        if len(self.line_ids) > 0:
            empty = False
        return empty

    def check_passenger_empty(self):
        empty = True
        for rec in self.passenger_ids:
            if rec.passenger_id is not empty or rec.pax_type is not empty:
                empty = False
        return empty

    # param_issued_offline_data = {
    #     "type": "airline",
    #     "total_sale_price": 100000,
    #     "desc": "amdaksd",
    #     "pnr": "10020120",
    #     "social_media_id": "Facebook",
    #     "expired_date": "2019-10-04 02:29",
    #     "line_ids": [
    #         {
    #             "pnr": "MUIQBF",
    #             "origin": "SUB",
    #             "destination": "SIN",
    #             "provider": "Garuda Indonesia",
    #             "departure": "2019-10-04 02:30",
    #             "arrival": "2019-10-04 02:30",
    #             "carrier_code": "SQ",
    #             "carrier_number": "a123",
    #             "sub_class": "B",
    #             "class_of_service": "eco"
    #         },
    #         {
    #             "pnr": "MUIQBF",
    #             "origin": "SIN",
    #             "destination": "SUB",
    #             "provider": "Garuda Indonesia",
    #             "departure": "2019-10-06 02:30",
    #             "arrival": "2019-10-06 02:30",
    #             "carrier_code": "SQ",
    #             "carrier_number": "a123",
    #             "sub_class": "B",
    #             "class_of_service": "eco"
    #         },
    #     ]
    # }

    # "type": "cruise",
    # "total_sale_price": 100000,
    # "desc": "Itinerary\n 02-05-2020: Singapore\n 03-05-2020: Surabaya\n 04-05-2020: Bali\n 05-05-2020: Surabaya\n 06-05-2020: Singapore",
    # # "pnr": "10020120",
    # "social_media_id": "Facebook",
    # "expired_date": "2019-10-04 02:29",
    # "quick_validate": True,
    # "line_ids": [
    #     {
    #         'pnr': 'NVIDIA',
    #         'provider': 'Genting Dream',
    #         'cruise_package': '4D3N Surabaya Bali Package',
    #         'departure_location': 'Singapore',
    #         'arrival_location': 'Singapore',
    #         'room': 'Balcony',
    #         'check_in': "2020-05-02",
    #         'check_out': "2020-05-05",
    #         'description': 'Itinerary\n 02-05-2020: Singapore\n 03-05-2020: Surabaya\n 04-05-2020: Bali\n 05-05-2020: Singapore'
    #     },
    #     {
    #         'pnr': 'AMDFTW',
    #         'provider': 'Royal Caribbean Cruise',
    #         'cruise_package': '5D/4N QUANTUM OF THE SEAS SINGAPORE MALAYSIA',
    #         'departure_location': 'Singapore',
    #         'arrival_location': 'Singapore',
    #         'room': 'Ocean View',
    #         'check_in': "2020-06-02",
    #         'check_out': "2020-06-06",
    #         'description': 'Itinerary\n 02-06-2020: Singapore\n 03-06-2020: Kuala Lumpur\n 04-06-2020: Penang\n 05-06-2020: Cruising\n 06-06-2020: Singapore'
    #     },
    # ]

    # "line_ids": [
    #     {
    #         "name": 1,
    #         "activity_package": 1,
    #         "qty": 1,
    #         "description": 'Test Activity',
    #         "visit_date": '2019-10-04',
    #     }
    # ]
    # "sector_type": "domestic"

    #         {
    #             "origin": "SIN",
    #             "destination": "HKG",
    #             "provider": "Singapore Airlines",
    #             "departure": "2019-10-04 02:30",
    #             "arrival": "2019-10-04 02:30",
    #             "carrier_code": "SQ",
    #             "carrier_number": "a123",
    #             "sub_class": "B",
    #             "class_of_service": "eco"
    #         },
    #     ]
    # }

    param_issued_offline_data = {
        "sector_type": "domestic",
        "quick_validate": True,
        "type": "airline",
        "total_sale_price": 100000,
        "desc": "amdaksd",
        # "pnr": "10020120",
        "social_media_id": "Facebook",
        "expired_date": "2019-10-04 02:29",
        "line_ids": [
            {
                "pnr": "MUIQBF",
                "origin": "SUB",
                "destination": "SIN",
                "provider": "Garuda Indonesia",
                "departure": "2019-10-04 02:30",
                "arrival": "2019-10-04 04:30",
                "carrier_code": "GA",
                "carrier_number": "X4333",
                "sub_class": "Y",
                "class_of_service": "eco"
            },
            {
                "pnr": "QOFUIH",
                "origin": "SIN",
                "destination": "HKG",
                "provider": "Singapore Airlines",
                "departure": "2019-10-06 12:30",
                "arrival": "2019-10-06 16:30",
                "carrier_code": "SQ",
                "carrier_number": "832",
                "sub_class": "Y",
                "class_of_service": "eco"
            },
            {
                "pnr": "VHYAUE",
                "origin": "HKG",
                "destination": "SUB",
                "provider": "Cathay Pacific",
                "departure": "2019-10-06 12:30",
                "arrival": "2019-10-06 16:30",
                "carrier_code": "CX",
                "carrier_number": "912",
                "sub_class": "Y",
                "class_of_service": "eco"
            },
        ]
    }

    # param_issued_offline_data = {
    #     "type": "activity",
    #     "total_sale_price": 100000,
    #     "desc": "amdaksd",
    #     # "pnr": "10020120",
    #     "social_media_id": "Facebook",
    #     "expired_date": "2019-10-04 02:29",
    #     "line_ids": [
    #         {
    #             "name": 'Universal Studios Singapore',
    #             "activity_package": 'Universal Studios Singapore 1 Day Pass',
    #             "qty": 1,
    #             "description": 'Test Activity',
    #             "visit_date": '2019-10-04',
    #         }
    #     ]
    #     # "sector_type": "domestic"
    # }

    # param_issued_offline_data = {
    #     "type": "hotel",
    #     "total_sale_price": 2000000,
    #     "desc": "amdaksd",
    #     # "pnr": "10020120",
    #     "social_media_id": "Facebook",
    #     "expired_date": "2019-10-04 02:29",
    #     "line_ids": [
    #         {
    #             "name": 'Jayakarta Hotel & Resort',
    #             "room": 'Deluxe',
    #             "meal_type": 'With Breakfast',
    #             "pnr": 'OINMDF',
    #             "qty": 2,
    #             "description": 'Jemput di bandara',
    #             "check_in": '2019-10-04',
    #             "check_out": '2019-10-06'
    #         },
    #         {
    #             "name": 'Wina Holiday Villa',
    #             "room": 'Superior',
    #             "meal_type": 'Room Only',
    #             "pnr": '',
    #             "qty": 2,
    #             "description": 'Jemput di bandara',
    #             "check_in": '2019-10-04',
    #             "check_out": '2019-10-06'
    #         },
    #         # {
    #         #     "name": 'Mercure Kuta Beach Bali',
    #         #     "room": 'Deluxe',
    #         #     "meal_type": 'Breakfast + Dinner',
    #         #     "pnr": '',
    #         #     "qty": 1,
    #         #     "description": 'Jemput di bandara',
    #         #     "check_in": '2019-10-04',
    #         #     "check_out": '2019-10-07'
    #         # },
    #         # {
    #         #     "name": 'Harris Resort Kuta Beach Bali',
    #         #     "room": 'Presidential',
    #         #     "meal_type": '',
    #         #     "pnr": '',
    #         #     "qty": 1,
    #         #     "description": 'Jemput di bandara',
    #         #     "check_in": '2019-10-04',
    #         #     "check_out": '2019-10-07'
    #         # },
    #     ]
    #     # "sector_type": "domestic"
    # }

    # param_issued_offline_data = {
    #     "type": "tour",
    #     "total_sale_price": 100000,
    #     "desc": "amdaksd",
    #     "pnr": "10020120",
    #     "social_media_id": "Facebook",
    #     "expired_date": "2019-10-04 02:29",
    #     "line_ids": [
    #         {
    #             "pnr": "5D BANGKOK PATTAYA BY SQ 21-25 MARET 2020",
    #             "description": "5D BANGKOK PATTAYA BY SQ 21-25 MARET 2020",
    #         },
    #         # {
    #         #     "origin": "SIN",
    #         #     "destination": "HKG",
    #         #     "provider": "Singapore Airlines",
    #         #     "departure": "2019-10-04 02:30",
    #         #     "arrival": "2019-10-04 02:30",
    #         #     "carrier_code": "SQ",
    #         #     "carrier_number": "a123",
    #         #     "sub_class": "B",
    #         #     "class_of_service": "eco"
    #         # },
    #         # {
    #         #     "origin": "HKG",
    #         #     "destination": "SUB",
    #         #     "provider": "Cathay Pacific",
    #         #     "departure": "2019-10-04 02:30",
    #         #     "arrival": "2019-10-04 02:30",
    #         #     "carrier_code": "CP",
    #         #     "carrier_number": "a123",
    #         #     "sub_class": "B",
    #         #     "class_of_service": "eco"
    #         # },
    #     ],
    #     # "sector_type": "domestic"
    # }

    param_booker = {
        "title": "MR",
        "first_name": "ivan",
        "last_name": "suryajaya",
        "email": "asd@gmail.com",
        "calling_code": "62",
        "mobile": "81283182321",
        "nationality_name": "Indonesia",
        "nationality_code": "ID",
        "booker_id": ""
    }

    param_contact = [
        {
            "title": "MR",
            "first_name": "ivan",
            "last_name": "suryajaya",
            "email": "asd@gmail.com",
            "calling_code": "62",
            "mobile": "81283182321",
            "nationality_name": "Indonesia",
            "nationality_code": "ID",
            "contact_id": "",
            "is_booker": True
        }
    ]

    param_passenger = [
        {
            "pax_type": "ADT",
            "first_name": "ivan",
            "last_name": "suryajaya",
            "title": "MSTR",
            "birth_date": "1987-08-25",
            "nationality_name": "Indonesia",
            "nationality_code": "ID",
            "country_of_issued_code": "Indonesia",
            "passport_expdate": "2019-10-04",
            "passport_number": "1231312323",
            "passenger_id": "",
            "is_booker": True,
            "is_contact": False
        },
        {
            "pax_type": "CHD",
            "first_name": "andy",
            "last_name": "sanjaya",
            "title": "MR",
            "birth_date": "1990-02-10",
            "nationality_name": "Indonesia",
            "nationality_code": "ID",
            "country_of_issued_code": "Indonesia",
            "passport_expdate": "2019-10-04",
            "passport_number": "1231312324",
            "passenger_id": "",
            "is_booker": True,
            "is_contact": False
        }
    ]

    param_context = {
        'co_uid': 8,
        'co_agent_id': 2,
        'co_agent_type_id': 2
    }

    param_payment = {
        "member": False,
        "seq_id": "PQR.2211082",
        # "member": False,
        # "seq_id": "PQR.0429001"
    }

    def get_config_api(self):
        try:
            res = {
                'sector_type': self._fields['sector_type'].selection,
                'transaction_type': [{'code': rec.code, 'name': rec.name} for rec in
                                     self.env['tt.provider.type']
                                         .search([('code', '!=', self.env.ref('tt_reservation_offline.tt_provider_type_offline').code)])],
                'carrier_id': [{'code': rec.code, 'name': rec.name, 'icao': rec.icao} for rec in
                               self.env['tt.transport.carrier'].search([])],
                'social_media_id': [{'name': rec.name} for rec in self.env['res.social.media.type'].search([])],
            }
            res['transaction_type'].append({
                'code': 'other',
                'name': 'Other'
            })
            res = Response().get_no_error(res)
        except Exception as e:
            res = Response().get_error(str(e), 500)
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
        return res

    def get_booking_offline_api(self, data, context):  #
        try:
            _logger.info("Get req\n" + json.dumps(context))
            book_obj = self.get_book_obj(data.get('book_id'), data.get('order_number'))
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)
            if book_obj.agent_id.id == context.get('co_agent_id', -1):
                res_dict = book_obj.sudo().to_dict()
                lines = []
                passengers = []
                attachments = []

                # lines
                for line in book_obj.line_ids:
                    lines.append(line.to_dict())

                # passengers
                for idx, psg in enumerate(book_obj.passenger_ids):
                    passengers.append(psg.to_dict())
                    passengers[len(passengers)-1].update({
                        'sequence': int(idx)
                    })

                # attachments
                for attachment in book_obj.attachment_ids:
                    attachments.append({
                        'name': attachment.name,
                        'filename': attachment.filename,
                        'url': attachment.url,
                        'owner': attachment.agent_id.name,
                    })

                res = {
                    'order_number': book_obj.name,
                    'hold_date': book_obj.hold_date and book_obj.hold_date.strftime('%d-%m-%Y %H:%M') or '',
                    'pnr': book_obj.pnr,
                    'state': book_obj.state,
                    'state_offline': book_obj.state_offline,
                    'offline_provider_type': book_obj.offline_provider_type,
                    'lines': lines,
                    'passengers': passengers,
                    'total': book_obj.total,
                    'commission': book_obj.agent_commission,
                    'currency': book_obj.currency_id.name,
                    'attachment': attachments
                }
                print(res)
                _logger.info("Get resp\n" + json.dumps(res))
                return Response().get_no_error(res)
            else:
                raise RequestException(1001)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def create_booking_reservation_offline_api(self, data, context):  #
        booker = data['booker']  # self.param_booker
        data_reservation_offline = data['issued_offline_data']  # self.param_issued_offline_data
        passengers = data['passenger']  # self.param_passenger
        contact = data['contact']  # self.param_contact
        context = context  # self.param_context
        lines = data['issued_offline_data']['line_ids']  # data_reservation_offline['line_ids']
        payment = data['payment']  # self.param_payment

        try:
            booker_id = self.create_booker_api(booker, context)  # create booker
            contact_id = self.create_contact_api(contact[0], booker_id, context)
            passenger_ids = self.create_customer_api(passengers, context, booker_id, contact_id)  # create passenger
            booking_line_ids = []
            iss_off_psg_ids = []
            if data_reservation_offline['total_sale_price'] <= 0:
                raise RequestException(1004, additional_message='Total sale price must be greater than 0 (zero).')
            if not lines:
                raise RequestException(1004, additional_message='Lines can\'t be empty.')
            create_line_res = self._create_line(lines, data_reservation_offline)
            if create_line_res['error_code'] == 0:
                booking_line_ids = create_line_res['response']
            else:
                raise RequestException(1004, additional_message='Create line error.')
            if not passengers:
                raise RequestException(1004, additional_message='Passengers can\'t be empty.')
            create_psg_res = self._create_reservation_offline_order(passengers, passenger_ids, context)
            if create_psg_res['error_code'] == 0:
                iss_off_psg_ids = create_psg_res['response']
            else:
                raise RequestException(create_psg_res['error_code'])
            header_val = {
                'booker_id': booker_id.id,
                'passenger_ids': [(6, 0, iss_off_psg_ids)],
                # 'contact_ids': [(6, 0, contact_ids)],
                'contact_id': contact_id.id,
                # 'customer_parent_id': customer_parent_id,
                'line_ids': [(6, 0, booking_line_ids)],
                'offline_provider_type': data_reservation_offline.get('type'),
                'description': data_reservation_offline.get('desc'),
                'total': data_reservation_offline['total_sale_price'],
                "social_media_type": self._get_social_media_id_by_name(data_reservation_offline.get('social_media_id')),
                # "expired_date": data_reservation_offline.get('expired_date'),
                "hold_date": data_reservation_offline.get('expired_date'),
                "quick_validate": data_reservation_offline.get('quick_validate'),
                'state': 'draft',
                'state_offline': 'confirm',
                'agent_id': context['co_agent_id'],
                'user_id': context['co_uid'],
            }

            if data_reservation_offline['type'] == 'airline':
                header_val.update({
                    'sector_type': data_reservation_offline.get('sector_type'),
                })
            book_obj = self.sudo().create(header_val)
            book_obj.update({
                'total': data_reservation_offline['total_sale_price']
            })

            # COR / POR
            if payment.get('member'):
                customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', payment['seq_id'])],limit=1).id
            # cash / transfer
            else:
                # get payment acquirer
                if payment['seq_id']:
                    acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', payment['seq_id'])], limit=1)
                    if not acquirer_id:
                        raise RequestException(1017)
                else:
                    # raise RequestException(1017)
                    acquirer_id = book_obj.agent_id.default_acquirer_id
                book_obj.sudo().write({
                    'acquirer_id': acquirer_id.id,
                })
                customer_parent_id = book_obj.agent_id.customer_parent_walkin_id.id  # fpo

            book_obj.sudo().write({
                'customer_parent_id': customer_parent_id,
            })

            book_obj.action_confirm(context)
            response = {
                'order_number': book_obj.name
            }
            res = self.get_booking_offline_api(response, context)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            res = Response().get_error(str(e), 1004)
        return res

    def _create_line(self, lines, data_reservation_offline):
        line_list = []
        destination_env = self.env['tt.destinations'].sudo()
        line_env = self.env['tt.reservation.offline.lines'].sudo()
        provider_env = self.env['tt.transport.carrier'].sudo()
        provider_type = data_reservation_offline['type']
        print('Provider_type : ' + provider_type)
        try:
            if provider_type in ['airline', 'train']:
                for line in lines:
                    # print('Origin: ' + str(destination_env.search([('code', '=', line.get('origin'))], limit=1).name))
                    # print('Destination: ' + str(destination_env.search([('code', '=', line.get('destination'))], limit=1).name))
                    # print('Carrier : ' + str(provider_env.search([('name', '=', line.get('provider'))], limit=1).name))
                    departure_time = datetime.strptime(line.get('departure'), '%Y-%m-%d %H:%M')
                    arrival_time = datetime.strptime(line.get('arrival'), '%Y-%m-%d %H:%M')
                    line_tmp = {
                        "pnr": line.get('pnr'),
                        "origin_id": destination_env.search([('code', '=', line.get('origin'))], limit=1).id,
                        "destination_id": destination_env.search([('code', '=', line.get('destination'))], limit=1).id,
                        "provider": line.get('provider'),
                        "departure_date": departure_time.strftime('%Y-%m-%d'),
                        "departure_hour": str(departure_time.hour),
                        "departure_minute": str(departure_time.minute),
                        "arrival_date": arrival_time.strftime('%Y-%m-%d'),
                        "return_hour": str(arrival_time.hour),
                        "return_minute": str(arrival_time.minute),
                        "carrier_id": provider_env.search([('name', '=', line.get('provider'))], limit=1).id,
                        "carrier_code": line.get('carrier_code'),
                        "carrier_number": line.get('carrier_number'),
                        "subclass": line.get('sub_class'),
                        "class_of_service": line.get('class_of_service'),
                    }
                    line_obj = line_env.create(line_tmp)
                    line_list.append(line_obj.id)
            elif provider_type == 'hotel':
                for line in lines:
                    check_in = datetime.strptime(line.get('check_in'), '%Y-%m-%d')
                    check_out = datetime.strptime(line.get('check_out'), '%Y-%m-%d')
                    line_tmp = {
                        "pnr": line.get('pnr'),
                        "hotel_name": line.get('name'),
                        "room": line.get('room'),
                        "meal_type": line.get('meal_type'),
                        "obj_qty": line.get('qty'),
                        "description": line.get('description'),
                        "check_in": check_in.strftime('%Y-%m-%d'),
                        "check_out": check_out.strftime('%Y-%m-%d'),
                    }
                    line_obj = line_env.create(line_tmp)
                    line_list.append(line_obj.id)
            elif provider_type == 'activity':
                for line in lines:
                    visit_time = datetime.strptime(line.get('visit_date'), '%Y-%m-%d')
                    line_tmp = {
                        "pnr": line.get('pnr'),
                        "activity_name": line.get('name'),
                        "activity_package": line.get('activity_package'),
                        "qty": int(line.get('qty')),
                        "description": line.get('description'),
                        "visit_date": visit_time,
                    }
                    line_obj = line_env.create(line_tmp)
                    line_list.append(line_obj.id)
            elif provider_type == 'cruise':
                for line in lines:
                    check_in_time = datetime.strptime(line.get('check_in'), '%Y-%m-%d')
                    check_out_time = datetime.strptime(line.get('check_out'), '%Y-%m-%d')
                    line_tmp = {
                        "pnr": line.get('pnr'),
                        "cruise_package": line.get('cruise_package'),
                        "carrier_id": provider_env.search([('name', '=', line.get('provider'))], limit=1).id,
                        "departure_location": line.get('departure_location'),
                        "arrival_location": line.get('arrival_location'),
                        "room": line.get('room'),
                        "check_in": check_in_time.strftime('%Y-%m-%d'),
                        "check_out": check_out_time.strftime('%Y-%m-%d'),
                        "description": line.get('description')
                    }
                    line_obj = line_env.create(line_tmp)
                    line_list.append(line_obj.id)
            else:
                for line in lines:
                    line_tmp = {
                        "pnr": line.get('pnr'),
                        "description": line.get('description')
                    }
                    line_obj = line_env.create(line_tmp)
                    line_list.append(line_obj.id)
            res = Response().get_no_error(line_list)
            return res
        except Exception as e:
            print('Error line : ' + str(e))
            _logger.error(traceback.format_exc())
            return ERR.get_error(1004, additional_message='Error create line : ' + str(e))

    def _create_reservation_offline_order(self, passengers, passenger_ids, context):
        iss_off_psg_env = self.env['tt.reservation.offline.passenger'].sudo()
        iss_off_pas_list = []
        try:
            for idx, psg in enumerate(passengers):
                psg_vals = {
                    'passenger_id': passenger_ids[idx][0].id,
                    'agent_id': context['co_agent_id'],
                    'pax_type': psg['pax_type'],  # 'OAM'
                    'title': psg['title']
                }
                iss_off_psg_obj = iss_off_psg_env.create(psg_vals)
                iss_off_pas_list.append(iss_off_psg_obj.id)
        except Exception as e:
            print('Error line : ' + str(e))
            _logger.error(traceback.format_exc())
            return ERR.get_error(1004, additional_message='Error create passenger : ' + str(e))
        res = Response().get_no_error(iss_off_pas_list)
        return res

    def _get_social_media_id_by_name(self, name):
        social_media_id = self.env['res.social.media.type'].search([('name', '=', name)], limit=1).id
        return social_media_id

    def check_provider_state(self, context, pnr_list=[], hold_date=False, req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            pass
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            pass
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            # refund
            self.action_refund()
        elif all(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.write({
                'state': 'fail_refunded',
                'state_offline': 'fail_refunded',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif any(rec.state == 'refund' for rec in self.provider_booking_ids):
            pass
        else:
            # entah status apa
            _logger.error('Entah status apa')
            raise RequestException(1006)

    def confirm_api(self, id):
        obj = self.sudo().browse(id)
        obj.action_confirm()

    def print_ho_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        offline_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_offline')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = offline_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = offline_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Offline HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Offline HO Invoice',
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
        # return offline_ho_invoice_id.report_action(self, data=datas)

    def randomizer_rec(self):
        import random
        list_agent_id = self.env['tt.agent'].sudo().search([]).ids
        list_provider_id = self.env['tt.provider.type'].sudo().search([]).ids
        for rec in self.sudo().search([], limit=1000):
            new_rec = rec.sudo().copy()
            new_rec.update({
                'agent_id': list_agent_id[random.randrange(0, len(list_agent_id)-1, 1)],
                'offline_provider_type': list_provider_id[random.randrange(0, len(list_provider_id)-1, 1)],
                'total': random.randrange(100000, 2000000, 5000),
                'agent_commission': random.randrange(1000, 20000, 500),
            })
        return True

    def get_aftersales_desc(self):
        desc_txt = ''
        if self.offline_provider_type in ['airline', 'train']:
            for rec in self.line_ids:
                desc_txt += 'PNR: ' + (rec.pnr or '') + '<br/>'
                desc_txt += 'Carrier: ' + (rec.carrier_id.name or '') + '<br/>'
                desc_txt += 'Departure: ' + (rec.origin_id.display_name or '') + ' (' + (rec.departure_date or '') + ' ' + (rec.departure_hour or '') + ':' + (rec.departure_minute or '') + ')<br/>'
                desc_txt += 'Arrival: ' + (rec.destination_id.display_name or '') + ' (' + (rec.arrival_date or '') + ' ' + (rec.return_hour or '') + ':' + (rec.return_minute or '') + ')<br/><br/>'
        elif self.offline_provider_type == 'hotel':
            for rec in self.line_ids:
                desc_txt += 'PNR: ' + (rec.pnr or '') + '<br/>'
                desc_txt += 'Hotel : ' + (rec.hotel_name or '') + '<br/>'
                desc_txt += 'Room : ' + (rec.room or '') + ' ' + str(rec.obj_qty) + 'x' + '<br/>'
                desc_txt += 'Date : ' + str(rec.check_in) + ' - ' + str(rec.check_out) + '<br/>'
                desc_txt += 'Passengers : ' + '<br/>'
                for idx, psg in enumerate(self.passenger_ids):
                    index = idx + 1
                    desc_txt += str(index) + '. ' + (psg.first_name or '') + ' ' + (psg.last_name or '') + '<br/>'
                desc_txt += 'Description : ' + (rec.description or '') + '<br/><br/>'
        elif self.offline_provider_type == 'activity':
            for rec in self.line_ids:
                desc_txt += 'PNR: ' + (rec.pnr or '') + '<br/>'
                desc_txt += 'Activity : ' + (rec.activity_name or '') + '<br/>'
                desc_txt += 'Package : ' + (rec.activity_package or '') + str(rec.obj_qty) + 'x' + '<br/>'
                desc_txt += 'Date : ' + str(rec.check_in) + '<br/>'
                desc_txt += 'Passengers : ' + '<br/>'
                for idx, psg in enumerate(rec.passenger_ids):
                    index = idx + 1
                    desc_txt += str(index) + '. ' + (psg.first_name or '') + ' ' + (psg.last_name or '') + '<br/>'
                desc_txt += 'Description : ' + (rec.description or '') + '<br/><br/>'
        elif self.offline_provider_type == 'cruise':
            for rec in self.line_ids:
                desc_txt += 'PNR: ' + (rec.pnr or '') + '<br/>'
                desc_txt += 'Cruise : ' + (rec.cruise_package or '') + '<br/>'
                desc_txt += 'Room : ' + (rec.room or '') + ' ' + str(rec.obj_qty) + '<br/>'
                desc_txt += 'Date : ' + str(rec.check_in) + ' - ' + str(rec.check_out) + '<br/>'
                desc_txt += 'Passengers : ' + '<br/>'
                for idx, psg in enumerate(rec.passenger_ids):
                    index = idx + 1
                    desc_txt += str(index) + '. ' + (psg.first_name or '') + ' ' + (psg.last_name or '') + '<br/>'
                desc_txt += 'Description : ' + (rec.description or '') + '<br/><br/>'
        else:
            for rec in self.line_ids:
                desc_txt += 'PNR: ' + rec.pnr + '<br/>'
                desc_txt += 'Description : ' + rec.description + '<br/><br/>'
        return desc_txt

    def to_dict(self):
        return {
            'agent_id': self.agent_id.id,
            'booker_id': self.booker_id.id,
            'contact_id': self.contact_id.id,
            'offline_provider_type': self.offline_provider_type,
            'offline_provider_type_name': self.offline_provider_type_name,
            'total': self.total,
            'description': self.description,
            'state': self.state,
            'state_offline': self.state_offline,
            'social_media_type': self.social_media_type.id
        }
