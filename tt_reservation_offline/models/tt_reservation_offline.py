from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import traceback
import copy
from ...tools.api import Response

_logger = logging.getLogger(__name__)

STATE_OFFLINE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('sent', 'Sent'),
    ('paid', 'Validate'),
    ('posted', 'Done'),
    ('refund', 'Refund'),
    ('expired', 'Expired'),
    ('cancel', 'Canceled')
]

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
    _inherit = ['tt.history', 'tt.reservation']
    _name = 'tt.reservation.offline'
    _order = 'name desc'
    _description = 'Rodex Model'

    sub_agent_id = fields.Many2one('tt.agent', 'Sub-Agent', readonly=True, states={'draft': [('readonly', False)]},
                                   help='COR / POR', related='booker_id.agent_id')

    state = fields.Selection(STATE_OFFLINE, 'State', default='draft')
    # type = fields.Selection(TYPE, required=True, readonly=True,
    #                         states={'draft': [('readonly', False)]}, string='Transaction Type')
    provider_type_id = fields.Many2one('tt.provider.type', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}, string='Transaction Type')
    provider_type_id_name = fields.Char('Transaction Name', readonly=True, related='provider_type_id.code')

    segment = fields.Integer('Number of Segment', compute='get_segment_length')
    person = fields.Integer('Person', readonly=True, states={'draft': [('readonly', False)],
                                                             'confirm': [('readonly', False)]})
    # carrier_id = fields.Many2one('tt.transport.carrier')
    sector_type = fields.Selection(SECTOR_TYPE, 'Sector', readonly=True, states={'draft': [('readonly', False)]})

    # 171121 CANDY: add field pnr, commission 80%, nta, nta 80%
    agent_commission = fields.Monetary('Agent Commission', readonly=True, compute='_get_agent_commission')
    parent_agent_commission = fields.Monetary('Parent Agent Commission', readonly=True, compute='_get_agent_commission')
    ho_commission = fields.Monetary('HO Commission', readonly=True, compute='_get_agent_commission')
    nta_price = fields.Monetary('NTA Price', readonly=True, compute='_get_nta_price')
    agent_nta_price = fields.Monetary('Agent NTA Price', readonly=True, compute='_get_agent_commission')

    vendor = fields.Char('Vendor Provider', readonly=True, states={'confirm': [('readonly', False)]})
    master_vendor_id = fields.Char('Master Vendor', readonly=True, states={'confirm': [('readonly', False)]})

    resv_code = fields.Char('Vendor Order Number', readonly=True, states={'paid': [('readonly', False)]})

    # Date and UID
    confirm_date = fields.Datetime('Confirm Date', readonly=True, copy=False)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True, copy=False)
    sent_date = fields.Datetime('Sent Date', readonly=True, copy=False)
    sent_uid = fields.Many2one('res.users', 'Sent by', readonly=True, copy=False)
    validate_date = fields.Datetime('Validate Date', readonly=True, copy=False)
    validate_uid = fields.Many2one('res.users', 'Validate by', readonly=True, copy=False)
    done_date = fields.Datetime('Done Date', readonly=True, copy=False)
    done_uid = fields.Many2one('res.users', readonly=True, copy=False)

    expired_date = fields.Datetime('Time Limit', readonly=True, states={'draft': [('readonly', False)]})

    # Monetary
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id,
                                  readonly=True, states={'draft': [('readonly', False)]})
    total_sale_price = fields.Monetary('Total Sale Price', readonly=True,
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    total_commission_amount = fields.Monetary('Total Commission Amount', readonly=True,
                                              states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # total_supplementary_price = fields.Monetary('Total Supplementary', compute='_get_total_supplement')
    total_tax = fields.Monetary('Total Taxes')

    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id,
                                 readonly=True)

    contact_id_backup = fields.Integer('Backup ID')

    invoice_ids = fields.Many2many('tt.agent.invoice', 'issued_invoice_rel', 'issued_id', 'invoice_id', 'Invoice(s)')
    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger(s)', domain=[('res_model', '=', 'tt.reservation.offline')])

    # Attachment
    attachment_ids = fields.Many2many('ir.attachment', 'tt_reservation_offline_rel',
                                      'tt_issued_id', 'attachment_id', domain=[('res_model', '=', 'tt.reservation.offline')]
                                      , string='Attachments', readonly=True, states={'paid': [('readonly', False)]})
    guest_ids = fields.Many2many('tt.customer', 'tt_issued_guest_rel', 'resv_issued_id', 'tt_product_id',
                                 'Guest(s)', readonly=True, states={'draft': [('readonly', False)]})
    # passenger_qty = fields.Integer('Passenger Qty', default=1)
    cancel_message = fields.Text('Cancellation Messages', copy=False)
    cancel_can_edit = fields.Boolean('Can Edit Cancellation Messages')

    description = fields.Text('Description', help='Itinerary Description like promo code, how many night or other info',
                              readonly=True,
                              states={'draft': [('readonly', False)]})

    line_ids = fields.One2many('tt.reservation.offline.lines', 'booking_id', 'Issued Offline', readonly=True,
                               states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.offline.passenger', 'booking_id', 'Issued Offline', readonly=True,
                                    states={'draft': [('readonly', False)]})

    incentive_amount = fields.Monetary('Insentif')
    vendor_amount = fields.Float('Vendor Amount', readonly=True,
                                 states={'paid': [('readonly', False), ('required', True)]})
    ho_final_amount = fields.Float('HO Amount')
    ho_final_ledger_id = fields.Many2one('tt.ledger')

    social_media_id = fields.Many2one('social.media.detail', 'Order From(Media)', readonly=True,
                                      states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_offline_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.tb.provider.offline', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})

    contact_ids = fields.One2many('tt.customer', 'reservation_offline_id', 'Contact Person', readonly=True,
                                  states={'draft': [('readonly', False)]})
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True,
                                states={'draft': [('readonly', False)]})
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True,
                                 states={'draft': [('readonly', False)]}, domain="[('agent_id', '=', agent_id)]")

    quick_issued = fields.Boolean('Quick Issued', default=False)

    # display_mobile = fields.Char('Contact Person for Urgent Situation',
    #                              readonly=True, states={'draft': [('readonly', False)]})
    # refund_id = fields.Many2one('tt.refund', 'Refund')

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
        return self.env.ref('tt_reservation_offline.action_report_printout_invoice_ticket').report_action(self, data=data)

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

    # STATE

    @api.one
    def action_confirm(self, kwargs={}):
        if not self.check_line_empty():
            if not self.check_passenger_empty():
                if self.total_sale_price != 0:
                    self.state = 'confirm'
                    self.confirm_date = fields.Datetime.now()
                    self.confirm_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
                    # self.send_push_notif()
                else:
                    raise UserError(_('Sale Price can\'t be 0 (Zero)'))
            else:
                raise UserError(_('Passenger(s) can\'t be 0 (Zero)'))
        else:
            raise UserError(_('Line(s) can\'t be empty'))

    @api.one
    def action_cancel(self):
        if self.state != 'posted':
            if self.state == 'paid':
                # # buat refund ledger
                # self.refund_ledger()
                # # cancel setiap invoice
                # for invoice in self.invoice_ids:
                #     invoice.action_cancel()
                self.create_reverse_ledger_offline()
            self.state = 'cancel'
            self.cancel_date = fields.Datetime.now()
            self.cancel_uid = self.env.user.id
            return True

    @api.one
    def action_draft(self):
        self.state = 'draft'
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
    def action_done(self, kwargs={}):
        # jika ada reservation code
        if self.resv_code:
            # jika ada attachment document
            if self.attachment_ids:
                # self.ho_final_ledger_id = self.final_ledger()
                # if self.agent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_citra').id, self.env.ref('tt_base_rodex.agent_type_japro').id]:
                # if self.agent_id.agent_type_id.name == 'Citra' or 'Japro':
                #     self.create_agent_invoice()
                self.state = 'posted'
                self.done_date = fields.Datetime.now()
                self.done_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
            else:
                raise UserError('No Attached Booking/Resv. Document')
        else:
            raise UserError('Please Add Vendor Order Number')

    @api.one
    def action_paid(self, kwargs={}):
        # cek saldo sub agent
        is_enough = self.agent_id.check_balance_limit_api(self.agent_id.id, self.total_sale_price)
        # jika saldo mencukupi
        if is_enough['error_code'] == 0:
            # self.validate_date = fields.Datetime.now()
            # self.validate_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
            self.issued_date = fields.Datetime.now()
            self.issued_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
            # create prices
            self.sudo().create_ledger_offline()
            # create ledger
            # self.sudo().create_ledger()
            # set state = paid
            self.state = 'paid'
            self.vendor_amount = self.nta_price
        return is_enough

    def check_pnr_empty(self):
        empty = True
        for rec in self.line_ids:
            if rec.pnr is not False:
                empty = False
        return empty

    def check_provider_empty(self):
        empty = True
        for rec in self.line_ids:
            if rec.provider_id is not False:
                empty = False
        return empty

    @api.one
    def action_sent(self):
        if self.provider_type_id_name is 'airline' or self.provider_type_id_name is 'train' or \
                self.provider_type_id_name is 'hotel' or self.provider_type_id_name is 'activity':
            if not self.check_provider_empty():
                if self.provider_type_id_name is 'airline' or self.provider_type_id_name is 'train':
                    if self.check_pnr_empty():
                        raise UserError(_('PNR(s) can\'t be Empty'))
            else:
                raise UserError(_('Provider(s) can\'t be Empty'))
        self.state = 'sent'
        self.sent_date = fields.Datetime.now()
        self.sent_uid = self.env.user.id

    @api.one
    def action_issued_backend(self):
        is_enough = self.action_paid()
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
                self.state = 'posted'
                self.book_date = fields.Datetime.now()
                self.book_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
            else:
                raise UserError('Attach Booking/Resv. Document')
        else:
            raise UserError('Add Vendor Order Number')

    @api.one
    def action_refund(self):
        self.state = 'refund'

    @api.one
    def action_quick_issued(self):
        if self.total_sale_price > 0 and self.nta_price > 0:
            for rec in self.line_ids:
                if not rec.pnr:
                    raise UserError(_('PNR can\'t be empty'))
            self.action_issued_backend()
        else:
            raise UserError(_('Sale Price or NTA Price can\'t be 0 (Zero)'))

    #################################################################################################

    # LEDGER & PRICES

    def create_ledger_offline(self):
        # fixme : comment dulu. tunggu tt_ledger
        provider_obj = self.env['tt.reservation.offline.lines'].search([('booking_id', '=', self.id)])
        # booking_obj = self.browse(self.id)

        try:
            # print(provider_obj)
            self.sudo().create_service_charge()
            self.sudo().create_ledger(provider_obj)
            self.sudo().create_ledger_agent_commission(provider_obj)
            self.sudo().create_ledger_parent_agent_commission(provider_obj)
            self.sudo().create_ledger_ho_commission(provider_obj)
            # provider_obj.action_create_ledger()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e) + '\nCreate ledger / service charge failed.'
            }

    def create_reverse_ledger_offline(self):
        provider_obj = self.env['tt.reservation.offline.lines'].search([('booking_id', '=', self.id)])

        try:
            self.sudo().create_reverse_ledger(provider_obj)
            self.sudo().create_reverse_ledger_agent_commission(provider_obj)
            self.sudo().create_reverse_ledger_parent_agent_commission(provider_obj)
            self.sudo().create_reverse_ledger_ho_commission(provider_obj)
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e) + '\nCreate ledger / service charge failed.'
            }

    def create_ledger(self, provider_obj):
        for rec in self:
            # Agent Ledger
            pnr = ''
            if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                pnr = self.get_pnr_list()

            # ledger_type = self.get_ledger_type()

            vals = self.env['tt.ledger'].prepare_vals('Resv : ' + rec.name, rec.name, rec.validate_date,
                                                      2, rec.currency_id.id, 0, rec.total_sale_price)
            vals = self.env['tt.ledger'].prepare_vals_for_resv(self, vals)
            vals.update({
                'pnr': pnr,
                'provider_type_id': self.provider_type_id,
                'display_provider_name': self.get_display_provider_name(),
                'issued_uid': self.env.user.id,
            })
            new_aml = rec.env['tt.ledger'].create(vals)

    def create_ledger_agent_commission(self, provider_obj):
        # Create Commission
        for rec in self:
            pnr = ''
            if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                pnr = self.get_pnr_list()

            if rec.agent_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, rec.name, rec.validate_date,
                                                           3, rec.currency_id.id, rec.agent_commission, 0)
                vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                vals1.update({
                    'pnr': pnr,
                    'provider_type_id': self.provider_type_id,
                    'display_provider_name': self.get_display_provider_name(),
                    'issued_uid': self.env.user.id,
                })
                commission_aml = rec.env['tt.ledger'].create(vals1)

    def create_ledger_parent_agent_commission(self, provider_obj):
        for rec in self:
            pnr = ''
            if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                pnr = self.get_pnr_list()

            if rec.parent_agent_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name,
                                                           rec.validate_date, 3, rec.currency_id.id,
                                                           rec.parent_agent_commission, 0)
                # vals1.update(vals_comm_temp)
                vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                vals1.update({
                    'agent_id': rec.agent_id.parent_agent_id.id,
                    'agent_type_id': rec.agent_id.parent_agent_id.agent_type_id.id,
                    'pnr': pnr,
                    'provider_type_id': self.provider_type_id,
                    'display_provider_name': self.get_display_provider_name(),
                    'issued_uid': self.env.user.id,
                })
                commission_aml = self.env['tt.ledger'].create(vals1)

    def create_ledger_ho_commission(self, provider_obj):
        for rec in self:
            pnr = ''
            if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                pnr = self.get_pnr_list()

            if rec.ho_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name + ' - REVERSE', 'HO: ' + rec.name,
                                                           rec.validate_date, 3, rec.currency_id.id,
                                                           rec.ho_commission, 0)
                # vals1.update(vals_temp)
                ho_agent = self.env['tt.agent'].sudo().search([('parent_agent_id', '=', False),
                                                               ('agent_type_id', '=', 'HO')], limit=1)
                vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                vals1.update({
                    'agent_id': ho_agent.id,
                    'agent_type_id': ho_agent.agent_type_id.id,
                    'pnr': pnr,
                    'provider_type_id': self.provider_type_id,
                    'issued_uid': self.env.user.id,
                    'display_provider_name': self.get_display_provider_name()
                })
                commission_aml = self.env['tt.ledger'].create(vals1)

    def create_reverse_ledger(self, provider_obj):
        for rec in self:
            pnr = ''
            if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                pnr = self.get_pnr_list()

            # ledger_type = self.get_ledger_type()

            vals = self.env['tt.ledger'].prepare_vals('Resv : ' + rec.name + ' - REVERSE', rec.name, rec.validate_date,
                                                      2, rec.currency_id.id, rec.total_sale_price, 0)
            vals = self.env['tt.ledger'].prepare_vals_for_resv(self, vals)
            vals.update({
                'pnr': pnr,
                'provider_type_id': self.provider_type_id,
                'issued_uid': self.env.user.id,
                'display_provider_name': self.get_display_provider_name()
            })
            new_aml = rec.env['tt.ledger'].create(vals)

    def create_reverse_ledger_agent_commission(self, provider_obj):
        for rec in self:
            # Create Commission
            pnr = ''
            if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                pnr = self.get_pnr_list()

            if rec.agent_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, rec.name, rec.validate_date,
                                                           3, rec.currency_id.id, 0, rec.agent_commission)
                vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                vals1.update({
                    'pnr': pnr,
                    'provider_type_id': self.provider_type_id,
                    'issued_uid': self.env.user.id,
                    'display_provider_name': self.get_display_provider_name()
                })
                commission_aml = rec.env['tt.ledger'].create(vals1)

    def create_reverse_ledger_parent_agent_commission(self, provider_obj):
        for rec in self:
            # Create Commission Parent Agent
            pnr = ''
            if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                pnr = self.get_pnr_list()

            if rec.parent_agent_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name,
                                                           rec.validate_date, 3, rec.currency_id.id, 0,
                                                           rec.parent_agent_commission)
                vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                # vals1.update(vals_comm_temp)
                vals1.update({
                    'agent_id': rec.agent_id.parent_agent_id.id,
                    'agent_type_id': rec.agent_id.parent_agent_id.agent_type_id.id,
                    'rel_agent_name': rec.agent_id.parent_agent_id.name,
                    'pnr': pnr,
                    'provider_type_id': self.provider_type_id,
                    'issued_uid': self.env.user.id,
                    'display_provider_name': self.get_display_provider_name()
                })
                commission_aml = self.env['tt.ledger'].create(vals1)

    def create_reverse_ledger_ho_commission(self, provider_obj):
        for rec in self:
            # Create Commission HO
            pnr = ''
            if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
                pnr = self.get_pnr_list()

            if rec.ho_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, 'HO: ' + rec.name,
                                                           rec.validate_date, 3, rec.currency_id.id,
                                                           0, rec.ho_commission)

                ho_agent = self.env['tt.agent'].sudo().search([('agent_type_id', '=', 'HO'),
                                                               ('parent_agent_id', '=', False)], limit=1)

                vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                vals1.update({
                    'agent_id': ho_agent.id,
                    'agent_type_id': ho_agent.agent_type_id.id,
                    'rel_agent_name': rec.agent_id.name,
                    'pnr': pnr,
                    'provider_type_id': self.provider_type_id,
                    'issued_uid': self.env.user.id,
                    'display_provider_name': self.get_display_provider_name()
                })
                commission_aml = self.env['tt.ledger'].create(vals1)
                commission_aml.action_done()

    def create_service_charge(self):
        service_chg_obj = self.env['tt.service.charge']
        res = self.generate_service_charge_summary()
        for val in res:
            for val_srvc in val['service_charges']:
                val_srvc.update({
                    'booking_offline_id': self.id,
                    # 'description': self.provider
                })
                print(val_srvc['amount'])
                # val['booking_id'] = self.id
                if val_srvc['amount'] > 0:
                    service_chg_obj.create(val_srvc)

    def generate_service_charge_summary(self):
        srvc_list = []
        if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
            total_passengers = len(self.passenger_ids)
            for psg in self.passenger_ids:
                srvc_list.append(self.get_service_charge_summary_airline_train(psg, total_passengers))
        elif self.provider_type_id_name == 'hotel':
            total_line = 0
            for line in self.line_ids:
                total_line += 1
            for line in self.line_ids:
                srvc_list.append(self.get_service_charge_summary_hotel(total_line))
        return srvc_list

    def get_service_charge_summary_airline_train(self, psg, total_passengers):
        res = {
            'service_charges': [
                {
                    'charge_code': 'fare',
                    'pax_type': psg.pax_type,
                    'pax_count': 1,
                    'amount': self.nta_price / total_passengers,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'rac',
                    'pax_type': psg.pax_type,
                    'pax_count': 1,
                    'amount': self.agent_commission,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'rac1',
                    'pax_type': psg.pax_type,
                    'pax_count': 1,
                    'amount': self.parent_agent_commission,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'rac2',
                    'pax_type': psg.pax_type,
                    'pax_count': 1,
                    'amount': self.ho_commission,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'roc',
                    'pax_type': psg.pax_type,
                    'pax_count': 1,
                    'amount': 0,
                    'currency': self.currency_id
                },
            ]
        }
        return res

    def get_service_charge_summary_hotel(self, total_line):
        res = {
            'service_charges': [
                {
                    'charge_code': 'fare',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': self.nta_price / total_line,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'rac',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': self.agent_commission,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'rac1',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': self.parent_agent_commission,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'rac2',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': self.ho_commission,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'roc',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': 0,
                    'currency': self.currency_id
                },
            ]
        }
        return res

    def get_service_charge_summary_activity(self):
        pass

    def get_service_charge_summary(self):
        response = {
            'pax_type': 'ADT',
            'service_charges': [
                {
                    'charge_code': 'fare',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': self.nta_price,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'r.ac',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': self.agent_commission,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'r.ac1',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': self.parent_agent_commission,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'r.ac2',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': self.ho_commission,
                    'currency': self.currency_id
                },
                {
                    'charge_code': 'r.oc',
                    'pax_type': 'ADT',
                    'pax_count': 1,
                    'amount': 0,
                    'currency': self.currency_id
                },
            ]
        }
        return response

    def get_ledger_type(self):
        if self.provider_type_id.code in ['airline', 'train', 'cruise']:
            vals = 'transport'
        elif self.provider_type_id.code == 'hotel':
            vals = 'hotel'
        elif self.provider_type_id.code == 'activity':
            vals = 'activity'
        elif self.provider_type_id.code == 'other':
            vals = 'other.min'
        elif self.provider_type_id.code == 'rent_car':
            vals = 'rent.car'
        elif self.provider_type_id.code == 'merchandise':
            vals = 'merchandise'
        else:
            vals = self.provider_type_id
        return vals

    ####################################################################################################

    # Set, Get & Compute

    # fixme mungkin akan diubah mekanisme perhitungannya

    @api.onchange('total_commission_amount', 'total_sale_price', 'segment', 'person')
    @api.depends('total_commission_amount', 'total_sale_price', 'segment', 'person')
    def _get_agent_commission(self):
        # pass
        for rec in self:
            pass
            # rec.agent_commission, rec.parent_agent_commission, rec.ho_commission = rec.sub_agent_type_id.calc_commission(
            #     rec.total_commission_amount, rec.segment * rec.person)
            # rec.agent_nta_price = rec.total_sale_price - rec.agent_commission

    @api.onchange('total_commission_amount')
    @api.depends('total_commission_amount', 'total_sale_price')
    def _get_nta_price(self):
        print('Sale Price : ' + str(self.total_sale_price))
        for rec in self:
            rec.nta_price = rec.total_sale_price - rec.total_commission_amount  # - rec.incentive_amount

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
                providers += rec
            return providers
        elif self.provider_type_id_name == 'hotel' or self.provider_type_id_name == 'activity':
            for rec in self.line_ids:
                found = False
                if rec.obj_name in provider_list:
                    found = True
                if found is False:
                    provider_list.append(rec.obj_name)
            providers = ''
            for rec in provider_list:
                providers += rec
            return providers
        else:
            return ''

    # Set provider berdasarkan carrier id
    # @api.onchange('carrier_id')
    # def set_provider(self):
    #     for rec in self:
    #         if rec.carrier_id:
    #             rec.provider = rec.carrier_id.name
    #         else:
    #             rec.provider = ''

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

    ####################################################################################################

    # CRON

    @api.multi
    def cron_set_expired(self):
        self.search([('expired_date', '>', fields.Datetime.now())])

    ####################################################################################################

    def get_config_api(self):
        try:
            res = {
                'sector_type': self._fields['sector_type'].selection,
                'transaction_type': [{'code': rec.code, 'name': rec.name} for rec in
                                     self.env['tt.provider.type'].search([])],
                'carrier_id': [{'code': rec.code, 'name': rec.name, 'icao': rec.icao} for rec in
                               self.env['tt.transport.carrier'].search([])],
                'social_media_id': [{'name': rec.name} for rec in self.env['social.media.detail'].search([])],
            }
            res = Response().get_no_error(res)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def create_booking_reservation_offline_api(self, data, context, kwargs):
        booker = data['booker']
        data_reservation_offline = data['issued_offline_data']
        passenger = data['passenger']
        contact = data['contact']
        context = context
        lines = data['issued_offline_data']['line_ids']

        try:
            user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
            # remove sementara update_api_context
            context.update({
                'agent_id': user_obj.agent_id.id,
                'user_id': user_obj.id
            })
            booker_id = self._create_booker(context, booker)  # create booker
            passenger_ids = self._create_passenger(context, passenger)  # create passenger
            # contact_ids = self._create_contact(context, contact)
            contact_id = self._create_contact(context, contact[0])
            customer_parent_id = self._set_customer_parent(context, contact_id)
            booking_line_ids = self._create_line(lines, data_reservation_offline)  # create booking line
            iss_off_psg_ids = self._create_reservation_offline_order(passenger)
            header_val = {
                'booker_id': booker_id,
                'passenger_ids': [(6, 0, iss_off_psg_ids)],
                # 'contact_ids': [(6, 0, contact_ids)],
                'contact_id': contact_id,
                'customer_parent_id': customer_parent_id,
                'line_ids': [(6, 0, booking_line_ids)],
                'provider_type_id': self.env['tt.provider.type'].sudo()
                                        .search([('code', '=', data_reservation_offline.get('type'))], limit=1).id,
                'description': data_reservation_offline.get('desc'),
                'total_sale_price': data_reservation_offline['total_sale_price'],
                "social_media_id": data_reservation_offline.get('social_media_id'),
                "expired_date": data_reservation_offline.get('expired_date'),
                'state': 'confirm',
                'agent_id': context['agent_id'],
                'user_id': context['co_uid'],
            }
            if data_reservation_offline['type'] == 'airline':
                header_val.update({
                    'sector_type': data_reservation_offline.get('sector_type'),
                })
            book_obj = self.create(header_val)
            book_obj.action_confirm(context)
            response = {
                'id': book_obj.name
            }
            res = Response().get_no_error(response)
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            res = Response().get_error(str(e), 500)
        return res

    def _create_booker(self, context, booker):
        country_env = self.env['res.country'].sudo()
        booker_env = self.env['tt.customer'].sudo()
        if booker['booker_id']:  # jika id booker ada
            booker['booker_id'] = int(booker['booker_id'])
            booker_rec = booker_env.browse(booker['booker_id'])
            if booker_rec:
                booker_rec.update({
                    'email': booker.get('email', booker_rec.email),
                    # 'mobile': vals.get('mobile', contact_rec.phone_ids[0]),
                })
            return booker_rec.id
        else:  # jika tidak ada id booker
            country = country_env.search([('code', '=', booker.pop('nationality_code'))])
            booker.update({
                'commercial_agent_id': context['agent_id'],
                'agent_id': context['agent_id'],
                'nationality_id': country and country[0].id or False,
                'email': booker.get('email', booker['email']),
                # 'mobile': booker.get('mobile', booker['mobile']),
            })
            booker_obj = booker_env.create(booker)
            booker_obj.update({
                'phone_ids': booker_obj.phone_ids.create({
                    'phone_number': booker.get('mobile', booker['mobile']),
                    'type': 'work'
                }),
            })
            return booker_obj.id

    def _create_contact(self, context, contact):
        contact_env = self.env['tt.customer'].sudo()
        country_env = self.env['res.country'].sudo()
        if contact['contact_id']:
            contact['contact_id'] = int(contact['contact_id'])
            contact_obj = contact_env.browse(contact['contact_id'])
            if contact_obj:
                contact_obj.update({
                    'email': contact.get('email', contact_obj.email),
                    # 'mobile': vals.get('mobile', contact_rec.phone_ids[0]),
                })
            return contact_obj.id
        else:
            country = country_env.search([('code', '=', contact.pop('nationality_code'))])  # diubah ke country_code
            contact.update({
                'commercial_agent_id': context['agent_id'],
                'agent_id': context['agent_id'],
                'nationality_id': country and country[0].id or False,
                # 'passenger_type': 'ADT',
                'email': contact.get('email', contact['email'])
            })
            contact_obj = contact_env.create(contact)
            contact_obj.update({
                'phone_ids': contact_obj.phone_ids.create({
                    'phone_number': contact.get('mobile', contact['mobile']),
                    'type': 'work'
                }),
            })
            return contact_obj.id
        # contact_list = []
        # contact_count = 0
        # for con in contact:
        #     contact_count += 1
        #     # cek jika sudah ada contact
        #     if con['contact_id']:
        #         con['contact_id'] = int(con['contact_id'])
        #         contact_rec = contact_env.browse(con['contact_id'])
        #         if contact_rec:
        #             contact_rec.update({
        #                 'email': con.get('email', contact_rec.email),
        #                 # 'mobile': vals.get('mobile', contact_rec.phone_ids[0]),
        #             })
        #         # return contact_rec
        #         contact_list.append(con['contact_id'])
        #     # jika tidak ada, buat customer baru
        #     else:
        #         country = country_env.search([('code', '=', con.pop('nationality_code'))])  # diubah ke country_code
        #         con.update({
        #             'commercial_agent_id': context['agent_id'],
        #             'agent_id': context['agent_id'],
        #             'nationality_id': country and country[0].id or False,
        #             # 'passenger_type': 'ADT',
        #             'email': con.get('email', con['email'])
        #         })
        #         contact_obj = contact_env.create(con)
        #         contact_obj.update({
        #             'phone_ids': contact_obj.phone_ids.create({
        #                 'phone_number': con.get('mobile', con['mobile']),
        #                 'type': 'work'
        #             }),
        #         })
        #         contact_list.append(contact_obj.id)
        # return contact_list

    def _create_contacts(self, context, contact):  # odoo10 : hanya 1 contact | odoo12 : bisa lebih dari 1 contact
        contact_env = self.env['tt.customer'].sudo()
        country_env = self.env['res.country'].sudo()
        contact_list = []
        contact_count = 0
        for con in contact:
            contact_count += 1
            # cek jika sudah ada contact
            if con['contact_id']:
                con['contact_id'] = int(con['contact_id'])
                contact_rec = contact_env.browse(con['contact_id'])
                if contact_rec:
                    contact_rec.update({
                        'email': con.get('email', contact_rec.email),
                        # 'mobile': vals.get('mobile', contact_rec.phone_ids[0]),
                    })
                # return contact_rec
                contact_list.append(con['contact_id'])
            # jika tidak ada, buat customer baru
            else:
                country = country_env.search([('code', '=', con.pop('nationality_code'))])  # diubah ke country_code
                con.update({
                    'commercial_agent_id': context['agent_id'],
                    'agent_id': context['agent_id'],
                    'nationality_id': country and country[0].id or False,
                    # 'passenger_type': 'ADT',
                    'email': con.get('email', con['email'])
                })
                contact_obj = contact_env.create(con)
                contact_obj.update({
                    'phone_ids': contact_obj.phone_ids.create({
                        'phone_number': con.get('mobile', con['mobile']),
                        'type': 'work'
                    }),
                })
                contact_list.append(contact_obj.id)
        return contact_list

    def _set_customer_parent(self, context, contact):
        customer_parent_env = self.env['tt.customer.parent']
        print('Agent ID : ' + str(context['agent_id']))
        agent_obj = self.env['tt.agent'].search([('id', '=', context['agent_id'])])
        # customer_parent_obj = customer_parent_env.sudo().search([('name', '=', context.agent_id.name + ' FPO')], limit=1)
        walkin_obj = agent_obj.customer_parent_walkin_id
        if walkin_obj:
            walkin_obj.write({
                'customer_ids': [(4, contact)]
            })
            return walkin_obj.id
        else:
            # create new Customer Parent FPO
            walkin_obj = customer_parent_env.create(
                {
                    'parent_agent_id': context['agent_id'],
                    'customer_parent_type_id': self.env.ref('tt_base.agent_type_fpo').id,
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

    def _create_passenger(self, context, passenger):
        passenger_list = []
        country_env = self.env['res.country'].sudo()
        passenger_env = self.env['tt.customer'].sudo()
        passenger_count = 0
        for psg in passenger:
            passenger_count += 1
            passenger_id = psg['passenger_id']
            if passenger_id:
                p_object = passenger_env.browse(int(passenger_id))
                if p_object:
                    passenger_list.append(passenger_id)
                    if psg.get('passport_number'):
                        p_object['passport_number'] = psg['passport_number']
                    if psg.get('passport_expdate'):
                        p_object['passport_expdate'] = psg['passport_expdate']
                    if psg.get('country_of_issued_id'):
                        p_object['country_of_issued_id'] = psg['country_of_issued_id']
                    print('Passenger Type : ' + str(psg['passenger_type']))
                    p_object.write({
                        'domicile': psg.get('domicile'),
                        # 'mobile': psg.get('mobile')
                    })
            else:
                country = country_env.search([('code', '=', psg.pop('nationality_code'))])
                psg['nationality_id'] = country and country[0].id or False
                if psg['country_of_issued_code']:
                    country = country_env.search([('code', '=', psg.pop('country_of_issued_code'))])
                    psg['country_of_issued_id'] = country and country[0].id or False
                if not psg.get('passport_expdate'):
                    psg.pop('passport_expdate')

                psg.update({
                    'passenger_id': False,
                    'agent_id': context['agent_id']
                })
                psg_res = passenger_env.create(psg)
                psg.update({
                    'passenger_id': psg_res.id,
                })
                passenger_list.append(psg_res.id)
        return passenger_list

    def _create_line(self, lines, data_reservation_offline):
        line_list = []
        destination_env = self.env['tt.destinations'].sudo()
        line_env = self.env['tt.reservation.offline.lines'].sudo()
        provider_type = data_reservation_offline['type']
        print('Provider_type : ' + provider_type)
        if provider_type in ['airline', 'train']:
            for line in lines:
                print('Origin: ' + str(destination_env.search([('code', '=', line.get('origin'))], limit=1).name))
                print('Destination: ' + str(destination_env.search([('code', '=', line.get('destination'))], limit=1).name))
                line_tmp = {
                    "origin_id": destination_env.search([('code', '=', line.get('origin'))], limit=1).id,
                    "destination_id": destination_env.search([('code', '=', line.get('destination'))], limit=1).id,
                    "provider": line.get('provider'),
                    "departure_date": line.get('departure'),
                    "return_date": line.get('arrival'),
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
                    "provider": line.get('name'),
                    "obj_subname": line.get('room'),
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
                    "provider": line.get('name'),
                    "obj_subname": line.get('package'),
                    "qty": int(line.get('qty')),
                    "description": line.get('description'),
                    "visit_date": line.get('visit_date'),
                }
                line_obj = line_env.create(line_tmp)
                line_list.append(line_obj.id)
        return line_list

    def _create_reservation_offline_order(self, passenger):
        iss_off_psg_env = self.env['tt.reservation.offline.passenger'].sudo()
        iss_off_pas_list = []
        for psg in passenger:
            psg_vals = {
                'passenger_id': psg['passenger_id'],
                'agent_id': self.env.user.agent_id.id,
                'pax_type': psg['pax_type']
            }
            iss_off_psg_obj = iss_off_psg_env.create(psg_vals)
            iss_off_pas_list.append(iss_off_psg_obj.id)
        return iss_off_pas_list

    def create_reservation_offline_by_api(self, vals, api_context=None):
        # Notes: SubmitTopUp
        # list_obj = []
        # list_line = []
        # for rec in vals['passenger_ids']:
        #     a = self.env['tt.reservation.offline.passenger'].create({
        #         'passenger_id': rec.get('id')
        #     })
        #     list_obj.append(a.id)
        # for rec in vals['line_ids']:
        #     origin = self.get_destination_id(vals['type'], rec['origin'])
        #     destination = self.get_destination_id(vals['type'], rec['destination'])
        #     a = self.env['tt.reservation.offline.lines'].create({
        #         'origin_id': origin,
        #         'destination_id': destination,
        #         'carrier_code': rec['carrier_code'],
        #         'carrier_number': rec['carrier_number'],
        #         'departure_date': rec['departure'],
        #         'return_date': rec['arrival'],
        #         'class_of_service': rec['class_of_service'],
        #         'sub_class': rec['sub_class']
        #     })
        #     list_line.append(a.id)
        # values = {
        #     'agent_id': int(vals['agent_id']),
        #     'sub_agent_id': int(vals['sub_agent_id']),
        #     'sub_agent_type': int(vals['sub_agent_type']),
        #     'contact_id': int(vals['contact_id']),
        #     'type': vals['type'],
        #     'sector_type': vals['sector_type'] or '',
        #     'total_sale_price': int(vals['total_sale_price']) or 0,
        #     'agent_commission': 0,
        #     'parent_agent_commission': 0,
        #     'agent_nta_price': 0,
        #     'description': vals['desc'],
        #     'carrier_id': int(vals['carrier_id']),
        #     'provider': vals['provider'],
        #     'pnr': vals['pnr'],
        #     'social_media_id': int(vals['social_media_id']),
        #     'expired_date': vals['expired_date'],
        #     'create_uid': int(vals['co_uid']),
        #     'confirm_uid': int(vals['co_uid']),
        #     'passanger_ids': [(6, 0, list_obj)],
        #     'line_ids': [(6, 0, list_line)],
        # }
        # try:
        #     res = self.env['tt.reservation.offline'].sudo().create(values)
        # except Exception as e:
        #     errors = []
        #     errors.append(('Issued Offline Failure', str(e)))
        #     return {
        #         'error_code': 1,
        #         'error_msg': errors,
        #         'response': {
        #             'message': '',
        #         }
        #     }
        #
        # self.confirm_api(res.id)
        # return {
        #     'error_code': 0,
        #     'error_msg': '',
        #     'response': {
        #         'message': '',
        #         'name': res.name
        #     }
        # }
        pass

    def get_reservation_offline_api(self, req, api_context=None):
        pass

    # def get_reservation_offline_api(self, req, api_context=None):
    #     def comp_agent_issued_offline(rec):
    #         passenger = []
    #         # jika ada passenger
    #         if len(rec.passenger_ids) > 0:
    #             # untuk setiap passenger
    #             for pax in rec.passenger_ids:
    #                 # masukkan data passenger ke dalam array
    #                 passenger.append({
    #                     # name : Mr. Andre Doang
    #                     'name': pax.passenger_id.title + ' ' + pax.passenger_id.first_name + ' ' + pax.passenger_id.last_name
    #                     # pax_type :
    #                     # 'pax_type' : pax.passenger_id.pax_type
    #
    #                 })

    def confirm_api(self, id):
        obj = self.sudo().browse(id)
        obj.action_confirm()

    ####################################################################################################

    # INVOICE

    @api.multi
    def prepare_invoice_line(self):
        pass

        # res_values = []
        # line_name = ''
        # carrier_name = self.carrier_id and self.carrier_id.name or self.provider and self.provider or ''
        # desc = self.description and self.description or ''
        #
        # for line in self.line_ids:
        #     carrier_code = line.carrier_code and line.carrier_code or '' + ' '
        #     carrier_number = line.carrier_number and line.carrier_number or ''
        #     # Todo Bedakan origin destination dari tipe (airline => airport, train => station, cruise => ports)
        #     if self.type in ['airline', 'train', 'cruise']:
        #         dd = (datetime.strptime(str(line.departure_date), '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        #         rd = (datetime.strptime(str(line.return_date), '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        #         line_name += line.origin_id.name + ' - ' + line.destination_id.name + ' ' + dd + ' - ' \
        #                      + rd + ' ' + carrier_name + ' ' + carrier_code + ' ' + carrier_number + '\n'
        #
        # line_name += '\n'
        # for passenger in self.passenger_ids:
        #     pass_name = ''
        #     if passenger.passenger_id:
        #         title = passenger.passenger_id.title and passenger.passenger_id.title or ''
        #         last_name = passenger.passenger_id.last_name and passenger.passenger_id.last_name or ''
        #         pass_name = title + ' ' + passenger.passenger_id.first_name + ' ' + last_name
        #     vals = {
        #         'name': pass_name,
        #         'price_unit': self.total_sale_price / len(self.passenger_ids),
        #         # 'product_id': self.get_product_id(),
        #         'quantity': 1
        #     }
        #     res_values.append(vals)
        # if res_values:
        #     res_values[0]['name'] = line_name + ' ' + res_values[0]['name']
        # else:
        #     vals = {
        #         'name': line_name != '\n' and line_name or self.description and self.description or self.name,
        #         'price_unit': self.total_sale_price,
        #         # 'product_id': self.get_product_id(),
        #         'quantity': 1
        #     }
        #     res_values.append(vals)
        # return res_values

    @api.multi
    def create_agent_invoice(self):
        pass
        # def prepare_agent_invoice():
        #     return {
        #         'origin': self.name,
        #         'agent_id': self.agent_id.id,
        #         'sub_agent_id': self.sub_agent_id.id,
        #         'res_id': self.id,
        #         'contact_id': self.contact_id.id,
        #         'pnr': self.pnr,
        #         # 'payment_term_id': self.sub_agnet_id.property_payment_term_id and
        #         #                    self.sub_agent_id.property_payment_term_id.id or False
        #     }
        #
        # agent_invoice = self.env['tt.agent.invoice']
        # agennt_invoice_line = self.env['tt.agent.invoice.line']
        # vals_invoice_line = self.prepare_invoice_line()
        # if vals_invoice_line:
        #     invoice = agent_invoice.create(prepare_agent_invoice())
        #     invoice.sudo().write({
        #         'user_id': self.confirm_uid.id
        #     })
        #     for values_line in vals_invoice_line:
        #         values_line.update({
        #             'invoice_id': invoice.id
        #         })
        #         agennt_invoice_line.sudo().create(values_line)
        #     invoice.state_invoice = 'full'
        #     self.write({
        #         'invoice_ids': [(6, 0, [invoice.id])]
        #     })

    # @api.multi
    # def write(self, vals):
    #     if self.env.user.agent_id.agent:
    #         res = super(IssuedOffline, self).write(vals)
    #         return res
    #     else:
    #         raise