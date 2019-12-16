from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import traceback
import copy
from ...tools.api import Response
from ...tools.ERR import RequestException
from ...tools import variables

_logger = logging.getLogger(__name__)

STATE_OFFLINE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('sent', 'Sent'),
    ('validate', 'Validate'),
    ('done', 'Done'),
    ('refund', 'Refund'),
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
    # type = fields.Selection(TYPE, required=True, readonly=True,
    #                         states={'draft': [('readonly', False)]}, string='Transaction Type')
    provider_type_id = fields.Many2one('tt.provider.type', string='Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_offline.tt_provider_type_offline'))
    offline_provider_type_id = fields.Many2one('tt.provider.type')
    provider_type_id_name = fields.Char('Transaction Name', readonly=True, related='offline_provider_type_id.code')
    provider_booking_ids = fields.One2many('tt.provider.offline', 'booking_id', string='Provider Booking')

    segment = fields.Integer('Number of Segment', compute='get_segment_length')
    person = fields.Integer('Person', readonly=True, states={'draft': [('readonly', False)],
                                                             'confirm': [('readonly', False)]})
    # carrier_id = fields.Many2one('tt.transport.carrier')
    sector_type = fields.Selection(SECTOR_TYPE, 'Sector', readonly=True, states={'draft': [('readonly', False)]})

    # 171121 CANDY: add field pnr, commission 80%, nta, nta 80%
    agent_commission = fields.Monetary('Agent Commission', readonly=True, compute='_get_agent_commission')
    parent_agent_commission = fields.Monetary('Parent Agent Commission', readonly=True, compute='_get_agent_commission')
    ho_commission = fields.Monetary('HO Commission', readonly=True, compute='_get_agent_commission')
    # states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    nta_price = fields.Monetary('NTA Price', readonly=True, compute='_get_nta_price', store=True)
    agent_nta_price = fields.Monetary('Agent Price', readonly=True, compute='_get_agent_price', store=True)

    vendor = fields.Char('Vendor Provider', readonly=True, states={'confirm': [('readonly', False)]})
    master_vendor_id = fields.Char('Master Vendor', readonly=True, states={'confirm': [('readonly', False)]})

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

    expired_date = fields.Datetime('Time Limit', readonly=True, states={'draft': [('readonly', False)]})

    # Monetary
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id,
                                  readonly=True, states={'draft': [('readonly', False)]})
    total = fields.Monetary('Total Sale Price', store=True)
    total_commission_amount = fields.Monetary('Total Commission Amount')
    # total_supplementary_price = fields.Monetary('Total Supplementary', compute='_get_total_supplement')
    total_tax = fields.Monetary('Total Taxes')

    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id,
                                 readonly=True)

    contact_id_backup = fields.Integer('Backup ID')

    invoice_ids = fields.Many2many('tt.agent.invoice', 'issued_invoice_rel', 'issued_id', 'invoice_id', 'Invoice(s)')
    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger(s)', domain=[('res_model', '=', 'tt.reservation.offline')])

    # Attachment
    # attachment_ids = fields.Many2many('ir.attachment', 'tt_reservation_offline_rel',
    #                                   'tt_issued_id', 'attachment_id', domain=[('res_model', '=', 'tt.reservation.offline')]
    #                                   , string='Attachments', readonly=True, states={'paid': [('readonly', False)]})
    attachment_ids = fields.Many2many('tt.upload.center', 'offline_ir_attachments_rel', 'tt_issued_id',
                                      'attachment_id', string='Attachments')
    guest_ids = fields.Many2many('tt.customer', 'tt_issued_guest_rel', 'resv_issued_id', 'tt_product_id',
                                 'Guest(s)', readonly=True, states={'draft': [('readonly', False)]})
    # passenger_qty = fields.Integer('Passenger Qty', default=1)
    cancel_message = fields.Text('Cancellation Messages', copy=False)
    cancel_can_edit = fields.Boolean('Can Edit Cancellation Messages')

    description = fields.Text('Description', help='Itinerary Description like promo code, how many night or other info',
                              readonly=True, states={'draft': [('readonly', False)]})

    line_ids = fields.One2many('tt.reservation.offline.lines', 'booking_id', 'Issued Offline')
    passenger_ids = fields.One2many('tt.reservation.offline.passenger', 'booking_id', 'Issued Offline')

    incentive_amount = fields.Monetary('Insentif')
    vendor_amount = fields.Float('Vendor Amount')
    ho_final_amount = fields.Float('HO Amount', readonly=True, compute='compute_final_ho')
    ho_final_ledger_id = fields.Many2one('tt.ledger')

    # social_media_id = fields.Many2one('res.social.media.type', 'Order From(Media)', readonly=True,
    #                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    social_media_type = fields.Many2one('res.social.media.type', 'Order From(Media)')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_offline_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    contact_ids = fields.One2many('tt.customer', 'reservation_offline_id', 'Contact Person', readonly=True,
                                  states={'draft': [('readonly', False)]})
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True,
                                states={'draft': [('readonly', False)]})
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True,
                                 states={'draft': [('readonly', False)]}, domain="[('agent_id', '=', agent_id)]")
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True,
                                         states={'draft': [('readonly', False)]},
                                         help='COR / POR', domain="[('parent_agent_id', '=', agent_id)]")

    quick_issued = fields.Boolean('Quick Issued', default=False)

    acquirer_id = fields.Many2one('payment.acquirer', 'Payment Acquirer', readonly=True)

    # display_mobile = fields.Char('Contact Person for Urgent Situation',
    #                              readonly=True, states={'draft': [('readonly', False)]})
    # refund_id = fields.Many2one('tt.refund', 'Refund')

    ####################################################################################################
    # REPORT
    ####################################################################################################

    def print_invoice(self):
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        return self.env.ref('tt_reservation_offline.action_report_printout_invoice').report_action(self, data=data)

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
                    self.confirm_date = fields.Datetime.now()
                    self.confirm_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
                    self.acquirer_id = self.agent_id.default_acquirer_id
                    # self.send_push_notif()
                else:
                    raise UserError(_('Sale Price can\'t be 0 (Zero)'))
            else:
                raise UserError(_('Passenger(s) can\'t be 0 (Zero)'))
        else:
            raise UserError(_('Line(s) can\'t be empty'))

    @api.one
    def action_cancel(self):
        if self.state != 'done':
            if self.state == 'validate':
                # # buat refund ledger
                # self.refund_ledger()
                # # cancel setiap invoice
                # for invoice in self.invoice_ids:
                #     invoice.action_cancel()
                # self.create_reverse_ledger_offline()
                for rec in self.ledger_ids:
                    rec.reverse_ledger()
                    # ledger_obj.update({
                    #     'transaction_type': self.provider_type_id_name,
                    #     'description': rec.description
                    # })
            self.state = 'cancel'
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
        self.ledger_id = False
        self.sub_ledger_id = False
        self.commission_ledger_id = False
        self.cancel_ledger_id = False
        self.cancel_sub_ledger_id = False
        self.cancel_commission_ledger_id = False
        self.cancel_message = False
        self.resv_code = False

    @api.one
    def action_validate(self, kwargs={}):
        # cek saldo agent
        is_enough = self.agent_id.check_balance_limit_api(self.agent_id.id, self.agent_nta)
        # jika saldo mencukupi
        if is_enough['error_code'] == 0:
            # self.validate_date = fields.Datetime.now()
            # self.validate_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
            # create prices
            for provider in self.provider_booking_ids:
                # create pricing list
                if self.provider_type_id_name != 'hotel':
                    provider.create_service_charge()
                else:
                    provider.create_service_charge_hotel()
                # provider.action_create_ledger()

            req = {
                'book_id': self.id,
                'order_number': self.name,
                'acquirer_seq_id': self.acquirer_id.seq_id,
                'member': False
            }
            if self.customer_parent_id.customer_parent_type_id.id != self.env.ref('tt_base.customer_type_fpo').id:
                req.update({
                    'member': True
                })
            context = {
                'co_uid': self.env.user.id,
                'co_agent_id': self.agent_id.id
            }
            payment = self.payment_reservation_api('offline', req, context)
            if payment['error_code'] != 0:
                _logger.error(payment['error_msg'])
                raise UserError(_(payment['error_msg']))

            self.calculate_service_charge()
            self.state_offline = 'validate'
            self.vendor_amount = self.nta_price
            self.compute_final_ho()
            self.issued_date = fields.Datetime.now()
            self.issued_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
            for provider in self.provider_booking_ids:
                provider.issued_date = self.issued_date
                provider.issued_uid = self.issued_uid

        return is_enough

    def check_pnr_empty(self):
        empty = False
        for rec in self.line_ids:
            if rec.pnr is False:
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
        if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train' or \
                self.provider_type_id_name == 'hotel' or self.provider_type_id_name == 'activity'\
                or self.provider_type_id_name == 'cruise':
            if self.check_provider_empty() is False:
                self.get_provider_name()
                # pnr = self.get_pnr_list()
                if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                    if self.check_pnr_empty():
                        raise UserError(_('PNR(s) can\'t be Empty'))
            else:
                raise UserError(_('Provider(s) can\'t be Empty'))
        self.state = 'booked'
        self.state_offline = 'sent'
        self.hold_date = datetime.now() + timedelta(days=1)
        self.sent_date = fields.Datetime.now()
        self.sent_uid = self.env.user.id
        self.create_provider_offline()
        # self.update_provider_offline()
        for provider in self.provider_booking_ids:
            provider.confirm_date = self.confirm_date
            provider.confirm_uid = self.confirm_uid
            provider.sent_date = self.sent_date
            provider.sent_uid = self.sent_uid

    @api.one
    def action_issued_backend(self):
        is_enough = self.action_validate()
        if is_enough[0]['error_code'] != 0:
            raise UserError(is_enough[0]['error_msg'])

    @api.one
    def action_done(self,  kwargs={}):
        if self.resv_code:
            if self.provider_type_id_name is not 'airline' or self.provider_type_id_name is not 'train':
                if self.check_pnr_empty():
                    raise UserError(_('PNR(s) can\'t be Empty'))
            if self.attachment_ids:
                # self.ho_final_ledger_id = self.final_ledger()
                # if self.agent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_citra').id, self.env.ref('tt_base_rodex.agent_type_japro').id]:
                #     self.create_agent_invoice()
                self.state = 'issued'
                self.state_offline = 'done'
                self.done_date = fields.Datetime.now()
                self.done_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
                self.booked_date = fields.Datetime.now()
                self.booked_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
                self.create_final_ho_ledger(self)
            else:
                raise UserError('Attach Booking/Resv. Document')
        else:
            raise UserError('Add Vendor Order Number')

    @api.one
    def action_refund(self):
        self.state = 'refund'

    @api.one
    def action_quick_issued(self):
        if self.total > 0 and self.nta_price > 0:
            self.action_sent()
            self.action_issued_backend()
        else:
            raise UserError(_('Sale Price or NTA Price can\'t be 0 (Zero)'))

    #################################################################################################
    # LEDGER & PRICES
    ####################################################################################################

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

    def create_final_ho_ledger(self, provider_obj):
        for rec in self:
            if rec.nta_price > rec.vendor_amount:
                # Agent Ledger
                pnr = self.get_pnr_list()

                vals = self.env['tt.ledger'].prepare_vals(self._name, self.id, 'Resv : ' + rec.name, 'Profit&Loss: ' + rec.name,
                                                          rec.validate_date, 3, rec.currency_id.id, self.env.user.id,
                                                          rec.ho_final_amount, 0)
                vals = self.env['tt.ledger'].prepare_vals_for_resv(self, pnr, vals)
                vals.update({
                    'pnr': pnr,
                    'provider_type_id': self.offline_provider_type_id,
                    'display_provider_name': self.provider_name,
                })
                new_aml = rec.env['tt.ledger'].create(vals)
            else:
                # Agent Ledger
                pnr = self.get_pnr_list()

                vals = self.env['tt.ledger'].prepare_vals(self._name, self.id, 'Resv : ' + rec.name,
                                                          'Profit&Loss: ' + rec.name,
                                                          rec.validate_date, 3, rec.currency_id.id, self.env.user.id,
                                                          0, abs(rec.ho_final_amount))
                vals = self.env['tt.ledger'].prepare_vals_for_resv(self, pnr, vals)
                vals.update({
                    'pnr': pnr,
                    'provider_type_id': self.offline_provider_type_id,
                    'display_provider_name': self.provider_name,
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

    @api.multi
    def get_segment_length(self):
        for rec in self:
            rec.segment = len(rec.line_ids)

    def get_destination_id(self, type, code):
        if type == 'airline':
            type = 'airport'
        elif type == 'train':
            type = 'train-st'
        elif type == 'bus':
            type = 'bus-st'
        elif type == 'activity':
            type = 'activity'
        elif type == 'cruise':
            type = 'harbour'
        # elif type == 'tour':
        #     type = 'tour'

        dest = self.env['tt.destinations'].sudo().search([('code', '=', code), ('type', '=', type)], limit=1)
        return dest and dest[0].id or False
        # return dest or False

    def get_pnr_list(self):
        pnr = ''
        for prov in self.line_ids:
            pnr += prov.pnr + ' '
        return pnr

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

    @api.onchange('total_commission_amount')
    @api.depends('total_commission_amount')
    def _get_agent_commission(self):
        for rec in self:
            pricing_obj = rec.env['tt.pricing.agent'].sudo()
            commission_list = pricing_obj.get_commission(rec.total_commission_amount, rec.agent_id,
                                                         rec.offline_provider_type_id)
            print(commission_list)
            rec.agent_commission = 0
            rec.parent_agent_commission = 0
            rec.ho_commission = 0

            for comm in commission_list:
                if comm.get('code') == 'rac':
                    rec.agent_commission += comm.get('amount')
                elif comm.get('agent_type_id') == rec.env.ref('tt_base.rodex_ho').agent_type_id.id:
                    rec.ho_commission += comm.get('amount')
                else:
                    rec.parent_agent_commission += comm.get('amount')

    # @api.onchange('agent_commission', 'ho_commission')
    # @api.depends('agent_commission', 'ho_commission')
    # def _get_ho_commission(self):
    #     for rec in self:
    #         rec.ho_commission = 0
    #         pricing_obj = rec.env['tt.pricing.agent'].sudo()
    #         commission_list = pricing_obj.get_commission(rec.agent_commission, rec.agent_id, rec.offline_provider_type_id)
    #         for comm in commission_list:
    #             if comm.get('agent_type_id') == rec.env.ref('tt_base.rodex_ho').agent_type_id.id:
    #                 rec.ho_commission += comm.get('amount')

    # Hitung harga final / Agent NTA Price
    @api.onchange('vendor_amount', 'nta_price')
    def compute_final_ho(self):
        for rec in self:
            rec.ho_final_amount = rec.nta_price - rec.vendor_amount

    @api.onchange('master_vendor_id')
    def _compute_vendor_text(self):
        for rec in self:
            rec.vendor = rec.master_vendor_id.name

    @api.onchange('contact_id')
    def _filter_customer_parent(self):
        if self.contact_id:
            return {'domain': {
                'customer_parent_id': [('customer_ids', 'in', self.contact_id.id)]
            }}

    def get_provider_name(self):
        provider_list = []
        for rec in self.line_ids:
            if rec.provider_id:
                provider_list.append(rec.provider_id.name)
        self.provider_name = ', '.join(provider_list)

    def check_line_empty(self):
        empty = True
        if self.provider_type_id_name != 'airline' and self.provider_type_id_name != 'train' and self.provider_type_id_name != 'hotel' and self.provider_type_id_name != 'activity':
            empty = False
        else:
            if len(self.line_ids) > 0:
                empty = False
        return empty

    def check_passenger_empty(self):
        empty = True
        for rec in self.passenger_ids:
            if rec.passenger_id is not empty or rec.pax_type is not empty:
                empty = False
        return empty

    ####################################################################################################
    # CRON
    ####################################################################################################

    @api.multi
    def cron_set_expired(self):
        self.search([('expired_date', '>', fields.Datetime.now())])

    ####################################################################################################
    # CREATE
    ####################################################################################################

    # param_issued_offline_data = {
    #     "type": "activity",
    #     "total_sale_price": 100000,
    #     "desc": "amdaksd",
    #     # "pnr": "10020120",
    #     "social_media_id": "Facebook",
    #     "expired_date": "2019-10-04 02:29",
    #     "line_ids": [
    #         {
    #             "name": 1,
    #             "activity_package": 1,
    #             "qty": 1,
    #             "description": 'Test Activity',
    #             "visit_date": '2019-10-04',
    #         }
    #     ]
    #     # "sector_type": "domestic"
    # }

    param_issued_offline_data = {
        "type": "hotel",
        "total_sale_price": 100000,
        "desc": "amdaksd",
        # "pnr": "10020120",
        "social_media_id": "Facebook",
        "expired_date": "2019-10-04 02:29",
        "line_ids": [
            {
                "name": 'Jayakarta Hotel & Resort',
                "room": 'Deluxe',
                "meal_type": 'With Breakfast',
                "pnr": 'OINMDF',
                "qty": 1,
                "description": 'Jemput di bandara',
                "check_in": '2019-10-04',
                "check_out": '2019-10-07'
            },
            {
                "name": 'Wina Holiday Villa',
                "room": 'Superior',
                "meal_type": 'Room Only',
                "pnr": '',
                "qty": 1,
                "description": 'Jemput di bandara',
                "check_in": '2019-10-04',
                "check_out": '2019-10-07'
            },
            {
                "name": 'Mercure Kuta Beach Bali',
                "room": 'Deluxe',
                "meal_type": 'Breakfast + Dinner',
                "pnr": '',
                "qty": 1,
                "description": 'Jemput di bandara',
                "check_in": '2019-10-04',
                "check_out": '2019-10-07'
            },
            {
                "name": 'Harris Resort Kuta Beach Bali',
                "room": 'Presidential',
                "meal_type": '',
                "pnr": '',
                "qty": 1,
                "description": 'Jemput di bandara',
                "check_in": '2019-10-04',
                "check_out": '2019-10-07'
            },
        ]
        # "sector_type": "domestic"
    }

    # param_issued_offline_data = {
    #     "type": "airline",
    #     "total_sale_price": 100000,
    #     "desc": "amdaksd",
    #     "pnr": "10020120",
    #     "social_media_id": "Facebook",
    #     "expired_date": "2019-10-04 02:29",
    #     "line_ids": [
    #         {
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
    #     "sector_type": "domestic"
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
            "pax_type": "INF",
            "first_name": "ivan",
            "last_name": "suryajaya",
            "title": "MR",
            "birth_date": "2019-08-25",
            "nationality_name": "Indonesia",
            "nationality_code": "ID",
            "country_of_issued_code": "Indonesia",
            "passport_expdate": "2019-10-04",
            "passport_number": "1231312323",
            "passenger_id": "",
            "is_booker": True,
            "is_contact": False
        }
    ]

    param_context = {
        'co_uid': 308,
        'co_agent_id': 80
    }

    param_payment = {
        "member": False,
        "seq_id": "PQR.0429001"
        # "seq_id": "PQR.9999999"
    }

    def get_config_api(self):
        try:
            res = {
                'sector_type': self._fields['sector_type'].selection,
                'transaction_type': [{'code': rec.code, 'name': rec.name} for rec in
                                     self.env['tt.provider.type'].search([('code', 'in', ['airline', 'activity', 'hotel', 'train'])])],
                'carrier_id': [{'code': rec.code, 'name': rec.name, 'icao': rec.icao} for rec in
                               self.env['tt.transport.carrier'].search([])],
                'social_media_id': [{'name': rec.name} for rec in self.env['res.social.media.type'].search([])],
            }
            res = Response().get_no_error(res)
        except Exception as e:
            res = Response().get_error(str(e), 500)
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
        return res

    def create_booking_reservation_offline_api(self, data, context):  #
        booker = data['booker']  # self.param_booker
        data_reservation_offline = data['issued_offline_data']  # self.param_issued_offline_data
        passengers = data['passenger']  # self.param_passenger
        contact = data['contact']  # self.param_contact
        context = context  # self.param_context
        lines = data['issued_offline_data']['line_ids']  # data_reservation_offline['line_ids']
        payment = data['payment']  # self.param_payment

        try:
            # cek saldo
            balance_res = self.env['tt.agent'].check_balance_limit_api(context['co_agent_id'], data_reservation_offline['total_sale_price'])
            if balance_res['error_code'] != 0:
                _logger.error('Agent Balance not enough')
                raise RequestException(1007, additional_message="agent balance")

            user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
            # remove sementara update_api_context
            context.update({
                'agent_id': user_obj.agent_id.id,
                'user_id': user_obj.id
            })
            booker_id = self.create_booker_api(booker, context)  # create booker
            # passenger_ids = self._create_passenger(context, passenger)  # create passenger
            # contact_ids = self._create_contact(context, contact)
            # contact_id = self._create_contact(context, contact[0])
            contact_id = self.create_contact_api(contact[0], booker_id, context)
            passenger_ids = self.create_customer_api(passengers, context, booker_id, contact_id)  # create passenger
            # customer_parent_id = self._set_customer_parent(context, contact_id)
            booking_line_ids = self._create_line(lines, data_reservation_offline)  # create booking line
            iss_off_psg_ids = self._create_reservation_offline_order(passengers, passenger_ids)
            header_val = {
                'booker_id': booker_id.id,
                'passenger_ids': [(6, 0, iss_off_psg_ids)],
                # 'contact_ids': [(6, 0, contact_ids)],
                'contact_id': contact_id.id,
                # 'customer_parent_id': customer_parent_id,
                'line_ids': [(6, 0, booking_line_ids)],
                'offline_provider_type_id': self.env['tt.provider.type'].sudo()
                                                .search([('code', '=', data_reservation_offline.get('type'))], limit=1).id,
                'description': data_reservation_offline.get('desc'),
                'total': data_reservation_offline['total_sale_price'],
                "social_media_type": self._get_social_media_id_by_name(data_reservation_offline.get('social_media_id')),
                "expired_date": data_reservation_offline.get('expired_date'),
                'state': 'draft',
                'state_offline': 'confirm',
                # 'agent_id': context['co_agent_id'],
                # 'user_id': context['co_uid'],
            }

            if data_reservation_offline['type'] == 'airline':
                header_val.update({
                    'sector_type': data_reservation_offline.get('sector_type'),
                })
            book_obj = self.create(header_val)
            book_obj.update({
                'total': data_reservation_offline['total_sale_price']
            })

            if payment.get('member'):
                customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', payment['seq_id'])])
            else:
                customer_parent_id = book_obj.agent_id.customer_parent_walkin_id.id
            if payment.get('seq_id'):
                acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', payment['seq_id'])], limit=1)
                if not acquirer_id:
                    raise RequestException(1017)
                else:
                    book_obj.acquirer_id = acquirer_id.id

            book_obj.sudo().write({
                'customer_parent_id': customer_parent_id,
            })

            book_obj.action_confirm(context)
            response = {
                'id': book_obj.name
            }
            res = Response().get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            res = Response().get_error(str(e), 500)
        return res

    def _set_customer_parent(self, context, contact):
        customer_parent_env = self.env['tt.customer.parent']
        print('Agent ID : ' + str(context['co_agent_id']))
        agent_obj = self.env['tt.agent'].search([('id', '=', context['co_agent_id'])])
        # customer_parent_obj = customer_parent_env.sudo().search([('name', '=', context.agent_id.name + ' FPO')], limit=1)
        walkin_obj = agent_obj.customer_parent_walkin_id
        if walkin_obj:
            walkin_obj.write({
                'customer_ids': [(4, contact.id)]
            })
            return walkin_obj.id
        else:
            # create new Customer Parent FPO
            walkin_obj = customer_parent_env.create(
                {
                    'parent_agent_id': context['co_agent_id'],
                    'customer_parent_type_id': self.env.ref('tt_base.customer_type_fpo').id,
                    'name': agent_obj.name + ' FPO'
                }
            )
            agent_obj.sudo().write({
                'customer_parent_walkin_id': walkin_obj.id
            })
            walkin_obj.write({
                'customer_ids': [(4, contact)]
            })
            return walkin_obj.id

    def _create_line(self, lines, data_reservation_offline):
        line_list = []
        destination_env = self.env['tt.destinations'].sudo()
        line_env = self.env['tt.reservation.offline.lines'].sudo()
        provider_env = self.env['tt.transport.carrier'].sudo()
        provider_type = data_reservation_offline['type']
        print('Provider_type : ' + provider_type)
        if provider_type in ['airline', 'train']:
            for line in lines:
                print('Origin: ' + str(destination_env.search([('code', '=', line.get('origin'))], limit=1).name))
                print('Destination: ' + str(destination_env.search([('code', '=', line.get('destination'))], limit=1).name))
                print('Carrier : ' + str(provider_env.search([('name', '=', line.get('provider'))], limit=1).name))
                line_tmp = {
                    "pnr": line.get('pnr'),
                    "origin_id": destination_env.search([('code', '=', line.get('origin'))], limit=1).id,
                    "destination_id": destination_env.search([('code', '=', line.get('destination'))], limit=1).id,
                    "provider": line.get('provider'),
                    "departure_date": line.get('departure'),
                    "return_date": line.get('arrival'),
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
                line_tmp = {
                    "pnr": line.get('pnr'),
                    "hotel_name": line.get('name'),
                    "room": line.get('room'),
                    "meal_type": line.get('meal_type'),
                    "qty": int(line.get('qty')),
                    "description": line.get('description'),
                    "check_in": line.get('check_in'),
                    "check_out": line.get('check_out'),
                }
                line_obj = line_env.create(line_tmp)
                line_list.append(line_obj.id)
        elif provider_type == 'activity':
            for line in lines:
                line_tmp = {
                    "pnr": line.get('pnr'),
                    "activity_name": line.get('name'),
                    "activity_package": line.get('activity_package'),
                    "qty": int(line.get('qty')),
                    "description": line.get('description'),
                    "visit_date": line.get('visit_date'),
                }
                line_obj = line_env.create(line_tmp)
                line_list.append(line_obj.id)
        return line_list

    def _create_reservation_offline_order(self, passengers, passenger_ids):
        iss_off_psg_env = self.env['tt.reservation.offline.passenger'].sudo()
        iss_off_pas_list = []
        for idx, psg in enumerate(passengers):
            psg_vals = {
                'passenger_id': passenger_ids[idx][0].id,
                'agent_id': self.env.user.agent_id.id,
                'pax_type': psg['pax_type']
            }
            iss_off_psg_obj = iss_off_psg_env.create(psg_vals)
            iss_off_pas_list.append(iss_off_psg_obj.id)

        return iss_off_pas_list

    def _get_social_media_id_by_name(self, name):
        social_media_id = self.env['res.social.media.type'].search([('name', '=', name)], limit=1).id
        return social_media_id

    def check_provider_state(self, context, pnr_list=[], hold_date=False, req={}):
        if all(rec.state == 'draft' for rec in self.provider_booking_ids):
            pass
        elif all(rec.state == 'confirm' for rec in self.provider_booking_ids):
            pass
        elif all(rec.state == 'sent' for rec in self.provider_booking_ids):
            pass
        elif all(rec.state == 'validate' for rec in self.provider_booking_ids):
            pass
        elif all(rec.state == 'done' for rec in self.provider_booking_ids):
            pass
        else:
            # entah status apa
            _logger.error('Entah status apa')
            raise RequestException(1006)

    def confirm_api(self, id):
        obj = self.sudo().browse(id)
        obj.action_confirm()

    def randomizer_rec(self):
        import random
        list_agent_id = self.env['tt.agent'].sudo().search([]).ids
        list_provider_id = self.env['tt.provider.type'].sudo().search([]).ids
        for rec in self.sudo().search([], limit=1000):
            new_rec = rec.sudo().copy()
            new_rec.update({
                'agent_id': list_agent_id[random.randrange(0, len(list_agent_id)-1, 1)],
                'offline_provider_type_id': list_provider_id[random.randrange(0, len(list_provider_id)-1, 1)],
                'total': random.randrange(100000, 2000000, 5000),
                'agent_commission': random.randrange(1000, 20000, 500),
            })
        return True
