from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging,traceback

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
    _name = 'issued.offline'

    sub_agent_id = fields.Many2one('tt.agent', 'Sub-Agent', readonly=True, states={'draft': [('readonly', False)]},
                                   help='COR / POR', related='contact_id.agent_id')

    state = fields.Selection(STATE_OFFLINE, 'State', default='draft')
    # type = fields.Selection(TYPE, required=True, readonly=True,
    #                         states={'draft': [('readonly', False)]}, string='Transaction Type')
    provider_type_id = fields.Many2one('tt.provider.type', required=True, readonly=True,
                           states={'draft': [('readonly', False)]}, string='Transaction Type')

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

    # Ledger
    # ledger_id = fields.Many2one('tt.ledger', 'Ledger', copy=False)
    # sub_ledger_id = fields.Many2one('tt.ledger', 'Sub Agent', copy=False)
    # commission_ledger_id = fields.Many2one('tt.ledger', 'Commission', copy=False)
    # cancel_ledger_id = fields.Many2one('tt.ledger', 'Cancel Ledger', copy=False)
    # cancel_sub_ledger_id = fields.Many2one('tt.ledger', 'Cancel Sub Agent', copy=False)
    # cancel_commission_ledger_id = fields.Many2one('tt.ledger', 'Cancel Commission', copy=False)
    invoice_ids = fields.Many2many('tt.agent.invoice', 'issued_invoice_rel', 'issued_id', 'invoice_id', 'Invoice(s)')
    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger(s)', domain=[('res_model', '=', 'issued.offline')])

    # Attachment
    attachment_ids = fields.Many2many('ir.attachment', 'issued_offline_rel',
                                      'tt_issued_id', 'attachment_id', domain=[('res_model', '=', 'issued.offline')]
                                      , string='Attachments', readonly=True, states={'paid': [('readonly', False)]})
    guest_ids = fields.Many2many('tt.customer', 'tt_issued_guest_rel', 'resv_issued_id', 'tt_product_id',
                                 'Guest(s)', readonly=True, states={'draft': [('readonly', False)]})
    # passenger_qty = fields.Integer('Passenger Qty', default=1)
    cancel_message = fields.Text('Cancellation Messages', copy=False)
    cancel_can_edit = fields.Boolean('Can Edit Cancellation Messages')

    # start_date = fields.Datetime('Start Date', readonly=True,
    #                            states={'draft': [('readonly', False)]})
    # end_date = fields.Datetime('End Date', readonly=True,
    #                            states={'draft': [('readonly', False)]})
    description = fields.Text('Description', help='Itinerary Description like promo code, how many night or other info',
                              readonly=True,
                              states={'draft': [('readonly', False)]})
    # depart_city = fields.Many2one('res.country.city', 'Depart City', readonly=True,
    #                            states={'draft': [('readonly', False)]})
    # arrival_city = fields.Many2one('res.country.city', 'Arrival City', readonly=True,
    #                            states={'draft': [('readonly', False)]})

    line_ids = fields.One2many('issued.offline.lines', 'booking_id', 'Issued Offline', readonly=True,
                               states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    passenger_ids = fields.One2many('issued.offline.passenger', 'booking_id', 'Issued Offline', readonly=True,
                                    states={'draft': [('readonly', False)]})

    incentive_amount = fields.Monetary('Insentif')
    vendor_amount = fields.Float('Vendor Amount', readonly=True,
                                 states={'paid': [('readonly', False), ('required', True)]})
    ho_final_amount = fields.Float('HO Amount')
    ho_final_ledger_id = fields.Many2one('tt.ledger')

    social_media_id = fields.Many2one('social.media.detail', 'Order From(Media)', readonly=True,
                                      states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    cost_service_charge_ids = fields.One2many('tt.service.charge', 'booking_offline_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.tb.provider.offline', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})

    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True,
                                 states={'draft': [('readonly', False)]})
    # display_mobile = fields.Char('Contact Person for Urgent Situation',
    #                              readonly=True, states={'draft': [('readonly', False)]})
    # refund_id = fields.Many2one('tt.refund', 'Refund')
    # contact_id = fields.Many2one('tt.customer.contact', 'Booker / Contact')

    def check_line_empty(self):
        empty = True
        for rec in self.line_ids:
            if rec.provider is not False:
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
        if len(self.line_ids) > 0:
            line_empty = self.check_line_empty()
            if not line_empty:
                if len(self.passenger_ids) > 0 and self.provider_type_id.code != 'merchandise' or self.provider_type_id.code == 'merchandise':
                    passenger_empty = self.check_passenger_empty()
                    if not passenger_empty:
                        if self.total_sale_price != 0:
                            self.name = 'New'
                            if self.name == 'New':
                                self.name = self.env['ir.sequence'].next_by_code('issued.offline')
                            else:
                                self.name = self.name
                            self.state = 'confirm'
                            self.confirm_date = fields.Datetime.now()
                            self.confirm_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
                            # self.send_push_notif()
                        else:
                            raise UserError(_('Sale Price can\'t be 0 (Zero)'))
                    else:
                        raise UserError(_('Passenger(s) can\'t be 0 (Zero)'))
                else:
                    raise UserError(_('Passenger(s) can\'t be 0 (Zero)'))
            else:
                raise UserError(_('Line(s) can\'t be empty'))
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
        is_enough = self.env['tt.ledger'].check_balance_limit(self.sub_agent_id.id, self.total_sale_price)
        # jika saldo mencukupi
        if is_enough['error_code'] == 0:
            self.validate_date = fields.Datetime.now()
            self.validate_uid = kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
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

    @api.one
    def action_sent(self):
        if self.provider_type_id.code is 'airline' or 'train':
            if self.check_pnr_empty():
                raise UserError(_('PNR(s) can\'t be Empty'))
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
            if self.provider_type_id.code is 'hotel':
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

    # @api.one
    # def create_reverse_ledger(self):
    #     self.action_cancel()

    #################################################################################################

    # LEDGER & PRICES

    def create_ledger_offline(self):
        # fixme : comment dulu. tunggu tt_ledger
        provider_obj = self.env['issued.offline.lines'].search([('booking_id', '=', self.id)])
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
        provider_obj = self.env['issued.offline.lines'].search([('booking_id', '=', self.id)])

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
            ledger_type = self.get_ledger_type()
            vals = self.env['tt.ledger'].prepare_vals('Resv : ' + rec.name, rec.name, rec.validate_date,
                                                      ledger_type, rec.currency_id.id, 0, rec.total_sale_price)
            # vals['pnr'] = rec.pnr
            # vals['transport_type'] = rec.transport_type
            # vals['display_provider_id'] = rec.display_provider_id

            vals.update({
                'pnr': provider_obj.get_pnr_list(),
                'transport_type': rec.provider_type_id.code in ['airline', 'train', 'cruise'] and rec.provider_type_id.code or False,
                'display_provider_name': provider_obj.get_provider_list(),
                'provider_type': rec.provider_type_id.id,
                'description': 'Ledger',
                'res_id': rec.id,
                'res_model': rec._name,  #
                'validate_uid': rec.sudo().confirm_uid.id,
                'agent_id': rec.sub_agent_id.id,
                'agent_type_id': rec.sub_agent_type_id.id
            })

            # new_aml = rec.create_agent_ledger(vals)
            new_aml = rec.env['tt.ledger'].create(vals)

    def create_ledger_agent_commission(self, provider_obj):
        # Create Commission
        for rec in self:
            if rec.agent_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, rec.name, rec.validate_date,
                                                           'commission', rec.currency_id.id, rec.agent_commission, 0)
                # vals1.update(vals_comm_temp)
                vals1.update({
                    # 'agent_id': rec.sub_agent_id.parent_agent_id.id,
                    # 'agent_type_id': rec.sub_agent_id.parent_agent_id.agent_type_id.id,
                    'agent_id': rec.sub_agent_id.id,
                    'agent_type_id': rec.sub_agent_id.agent_type_id.id,
                    'display_provider_name': provider_obj.get_provider_list(),
                    'provider_type': rec.provider_type_id.id,
                    'pnr': provider_obj.get_pnr_list(),
                    'transport_type': rec.provider_type_id.code,
                    'description': 'Agent Commission',
                    'res_id': self.id,
                    'res_model': rec._name,
                    'validate_uid': rec.confirm_uid.id,
                })
                commission_aml = rec.env['tt.ledger'].create(vals1)
                # commission_aml = rec.create_sub_agent_ledger(vals1)
                # commission_aml.action_done()
                # rec.commission_ledger_id = commission_aml

    def create_ledger_parent_agent_commission(self, provider_obj):
        for rec in self:
            if rec.parent_agent_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name,
                                                           rec.validate_date, 'commission', rec.currency_id.id,
                                                           rec.parent_agent_commission, 0)
                # vals1.update(vals_comm_temp)
                vals1.update({
                    'agent_id': rec.sub_agent_id.parent_agent_id.id,
                    'agent_type_id': rec.sub_agent_id.parent_agent_id.agent_type_id.id,
                    'rel_agent_name': rec.sub_agent_id.name,
                    'display_provider_name': provider_obj.get_provider_list(),
                    'provider_type': rec.provider_type_id.id,
                    'pnr': provider_obj.get_pnr_list(),
                    'transport_type': rec.provider_type_id.code,
                    'description': 'Parent Agent Commission',
                    'res_id': self.id,
                    'res_model': rec._name,
                    'validate_uid': rec.confirm_uid.id,
                })
                commission_aml = self.env['tt.ledger'].create(vals1)

    def create_ledger_ho_commission(self, provider_obj):
        for rec in self:
            if rec.ho_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name + ' - REVERSE', 'HO: ' + rec.name,
                                                           rec.validate_date, 'commission', rec.currency_id.id,
                                                           rec.ho_commission, 0)
                # vals1.update(vals_temp)
                ho_agent = self.env['tt.agent'].sudo().search([('parent_agent_id', '=', False),
                                                               ('agent_type_id', '=', 'HO')], limit=1)
                vals1.update({
                    'agent_id': ho_agent.id,
                    'agent_type_id': ho_agent.agent_type_id.id,
                    'rel_agent_name': rec.sub_agent_id.name,
                    'display_provider_name': provider_obj.get_provider_list(),
                    'provider_type': rec.provider_type_id.id,
                    'pnr': provider_obj.get_pnr_list(),
                    'transport_type': rec.provider_type_id.code,
                    'description': 'HO Commisssion',
                    'res_id': self.id,
                    'res_model': rec._name,
                    'validate_uid': rec.confirm_uid.id,
                })
                commission_aml = self.env['tt.ledger'].create(vals1)

    def create_reverse_ledger(self, provider_obj):
        for rec in self:
            ledger_type = self.get_ledger_type()
            vals = self.env['tt.ledger'].prepare_vals('Resv : ' + rec.name + ' - REVERSE', rec.name, rec.validate_date,
                                                      ledger_type, rec.currency_id.id, rec.total_sale_price, 0)
            vals.update({
                'agent_id': rec.sub_agent_id.id,
                'agent_type_id': rec.sub_agent_type_id.id,
                'pnr': provider_obj.get_pnr_list(),
                'transport_type': rec.provider_type_id.code in ['airline', 'train', 'cruise'] and rec.provider_type_id or False,
                'display_provider_name': provider_obj.get_provider_list(),
                'provider_type': rec.provider_type_id.id,
                'description': 'Reverse Ledger',
                'res_id': rec.id,
                'res_model': rec._name,
                'validate_uid': rec.sudo().confirm_uid.id,
            })
            new_aml = rec.env['tt.ledger'].create(vals)
            # new_aml.action_done()
            # rec.ledger_id = new_aml

    def create_reverse_ledger_agent_commission(self, provider_obj):
        for rec in self:
            # Create Commission
            if rec.agent_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, rec.name, rec.validate_date,
                                                           'commission', rec.currency_id.id, 0, rec.agent_commission)
                # vals1.update(vals_comm_temp)
                vals1.update({
                    'agent_id': rec.sub_agent_id.id,
                    'agent_type_id': rec.sub_agent_id.agent_type_id.id,
                    'display_provider_name': provider_obj.get_provider_list(),
                    'pnr': provider_obj.get_pnr_list(),
                    'provider_type': rec.provider_type_id.id,
                    'transport_type': rec.provider_type_id.code,
                    'description': 'Reverse Agent Commission',
                    'res_id': self.id,
                    'res_model': rec._name,
                    'validate_uid': rec.confirm_uid.id,
                })
                commission_aml = rec.create_sub_agent_ledger(vals1)
                # commission_aml.action_done()
                # rec.commission_ledger_id = commission_aml

    def create_reverse_ledger_parent_agent_commission(self, provider_obj):
        for rec in self:
            # Create Commission Parent Agent
            if rec.parent_agent_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name,
                                                           rec.validate_date, 'commission', rec.currency_id.id, 0,
                                                           rec.parent_agent_commission)
                # vals1.update(vals_comm_temp)
                vals1.update({
                    'agent_id': rec.sub_agent_id.parent_agent_id.id,
                    'rel_agent_name': rec.sub_agent_id.parent_agent_id.name,
                    'display_provider_name': provider_obj.get_provider_list(),
                    'pnr': provider_obj.get_pnr_list(),
                    'provider_type': rec.provider_type_id.id,
                    'transport_type': rec.provider_type_id.code,
                    'description': 'Reverse Parent Agent Commission',
                    'res_id': self.id,
                    'res_model': rec._name,
                    'validate_uid': rec.confirm_uid.id,
                })
                commission_aml = self.env['tt.ledger'].create(vals1)
                # commission_aml.action_done()

    def create_reverse_ledger_ho_commission(self, provider_obj):
        for rec in self:
            # Create Commission HO
            if rec.ho_commission > 0:
                vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, 'HO: ' + rec.name,
                                                           rec.validate_date, 'commission', rec.currency_id.id,
                                                           0, rec.ho_commission)

                ho_agent = self.env['tt.agent'].sudo().search([('agent_type_id', '=', 'HO'),
                                                               ('parent_agent_id', '=', False)], limit=1)
                # vals1.update(vals_temp)
                vals1.update({
                    'agent_id': ho_agent.id,
                    'agent_type_id': ho_agent.agent_type_id.id,
                    'rel_agent_name': rec.sub_agent_id.name,
                    'display_provider_name': provider_obj.get_provider_list(),
                    'pnr': provider_obj.get_pnr_list(),
                    'provider_type': rec.provider_type_id.id,
                    'transport_type': rec.provider_type_id.code,
                    'description': 'Reverse HO Commission',
                    'res_id': self.id,
                    'res_model': rec._name,
                    'validate_uid': rec.confirm_uid.id,
                })
                commission_aml = self.env['tt.ledger'].create(vals1)
                commission_aml.action_done()

    def create_service_charge(self):
        service_chg_obj = self.env['tt.service.charge']
        res = self.get_service_charge_summary()
        for val in res['service_charges']:
            val.update({
                'booking_offline_id': self.id,
                # 'description': self.provider
            })
            # val['booking_id'] = self.id
            if val['amount'] > 0:
                service_chg_obj.create(val)

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
        elif self.provider_type_id == 'hotel':
            vals = 'hotel'
        elif self.provider_type_id == 'other':
            vals = 'other.min'
        elif self.provider_type_id == 'rent_car':
            vals = 'rent.car'
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
            rec.agent_commission, rec.parent_agent_commission, rec.ho_commission = rec.sub_agent_type_id.calc_commission(
                rec.total_commission_amount, rec.segment * rec.person)
            rec.agent_nta_price = rec.total_sale_price - rec.agent_commission

    @api.onchange('total_commission_amount')
    @api.depends('total_commission_amount', 'total_sale_price', 'incentive_amount')
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
        # elif type == 'activity':
        #     type = 'activity'
        elif type == 'cruise':
            type = 'harbour'
        # elif type == 'tour':
        #     type = 'tour'

        dest = self.env['tt.destinations'].sudo().search([('code', '=', code), ('type', '=', type)], limit=1)
        return dest and dest[0].id or False
        # return dest or False

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

    ####################################################################################################

    # CRON

    @api.multi
    def cron_set_expired(self):
        self.search([('expired_date', '>', fields.Datetime.now())])

    ####################################################################################################

    # API

    def create_issued_offline_by_api(self, vals, api_context=None):
        # Notes: SubmitTopUp
        # list_obj = []
        # list_line = []
        # for rec in vals['passenger_ids']:
        #     a = self.env['issued.offline.passenger'].create({
        #         'passenger_id': rec.get('id')
        #     })
        #     list_obj.append(a.id)
        # for rec in vals['line_ids']:
        #     origin = self.get_destination_id(vals['type'], rec['origin'])
        #     destination = self.get_destination_id(vals['type'], rec['destination'])
        #     a = self.env['issued.offline.lines'].create({
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
        #     res = self.env['issued.offline'].sudo().create(values)
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

    def get_issued_offline_api(self, req, api_context=None):
        pass

    # def get_issued_offline_api(self, req, api_context=None):
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
