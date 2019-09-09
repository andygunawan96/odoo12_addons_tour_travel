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
    agent_commission = fields.Monetary('Agent Commission', readonly=True,  # , compute='_get_agent_commission')
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    parent_agent_commission = fields.Monetary('Parent Agent Commission', readonly=True)  # , compute='_get_agent_commission'
    ho_commission = fields.Monetary('HO Commission', readonly=True,   # , compute='_get_agent_commission'
                                    states={'confirm': [('readonly', False)], 'confirm': [('readonly', False)]})
    nta_price = fields.Monetary('NTA Price', readonly=True, compute='_get_nta_price')
    agent_nta_price = fields.Monetary('Agent Price', readonly=True, compute='_get_agent_price')

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
                              readonly=True, states={'draft': [('readonly', False)]})

    line_ids = fields.One2many('tt.reservation.offline.lines', 'booking_id', 'Issued Offline', readonly=True,
                               states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.offline.passenger', 'booking_id', 'Issued Offline', readonly=True,
                                    states={'draft': [('readonly', False)]})

    incentive_amount = fields.Monetary('Insentif')
    vendor_amount = fields.Float('Vendor Amount', readonly=True,
                                 states={'paid': [('readonly', False), ('required', True)]})
    ho_final_amount = fields.Float('HO Amount', readonly=True, compute='compute_final_ho')
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
            self.sudo().create_ssc_ledger()
            # create ledger
            # self.sudo().create_ledger()
            # set state = paid
            self.state = 'paid'
            self.vendor_amount = self.nta_price
            self.compute_final_ho()
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
            if rec.provider_id is False:
                empty = True
        return empty

    @api.one
    def action_sent(self):
        if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train' or \
                self.provider_type_id_name == 'hotel' or self.provider_type_id_name == 'activity':
            if not self.check_provider_empty():
                if self.provider_type_id_name == 'airline' or self.provider_type_id_name == 'train':
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
                self.state = 'posted'
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
        if self.total_sale_price > 0 and self.nta_price > 0:
            for rec in self.line_ids:
                if not rec.pnr:
                    raise UserError(_('PNR can\'t be empty'))
            self.action_issued_backend()
        else:
            raise UserError(_('Sale Price or NTA Price can\'t be 0 (Zero)'))

    #################################################################################################

    # LEDGER & PRICES

    def create_ssc_ledger(self):
        provider_obj = self.env['tt.reservation.offline.lines'].search([('booking_id', '=', self.id)])
        try:
            service_charge_list = []
            if self.provider_type_id_name != 'hotel':
                total_passengers = len(self.passenger_ids)
                for psg in self.passenger_ids:
                    service_charge_list.append(self.get_service_charge_summary_airline_train(psg, total_passengers))
            else:
                total_line = len(self.line_ids)
                for line in self.line_ids:
                    service_charge_list.append((self.get_service_charge_summary_hotel(total_line)))
            service_charge_list = self.sudo().get_service_charge_list_offline(service_charge_list)
            self.sudo().create_service_charge_new(service_charge_list)
            self.sudo().create_ledger(provider_obj)
            self.sudo().create_ledger_commission(provider_obj)
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e) + '\nCreate ledger / service charge failed.'
            }

    def get_service_charge_list_offline(self, service_charge_list):
        new_sc_list = []
        total_pax = len(service_charge_list)
        for service_charge in service_charge_list:
            for sc in service_charge['service_charges']:
                found = False
                print(new_sc_list)
                if new_sc_list:
                    for new_sc in new_sc_list:
                        if new_sc['charge_code'] == sc['charge_code']:
                            if new_sc['pax_type'] == sc['pax_type']:
                                found = True
                                new_sc['pax_count'] = new_sc['pax_count'] + 1
                                new_sc['total'] = new_sc['amount'] * int(new_sc['pax_count'])
                                break
                if not found:
                    if sc['charge_type'] == 'FARE':
                        sc.update({
                            'total': sc['amount']
                        })
                    else:
                        sc.update({
                            'amount': sc['amount'] / total_pax,
                            'total': sc['amount'] / total_pax
                        })
                    new_sc_list.append(sc)
        # for HO Commission
        ho_agent = self.env['tt.agent'].sudo().search([('parent_agent_id', '=', False),
                                                       ('agent_type_id', '=', 'HO')], limit=1)
        new_sc_list.append({
            'agent_id': ho_agent.id,
            'agent_type_id': ho_agent.agent_type_id.id,
            'charge_type': 'RAC',
            'type': 'RAC',
            'charge_code': 'hoc',
            'code': 'hoc',
            'pax_count': 1,
            'pax_type': 'ADT',
            'amount': self.ho_commission,
            'total': self.ho_commission,
            'currency': self.currency_id,
        })
        return new_sc_list

    def create_service_charge_new(self, service_charge_list):
        for ssc in self.sale_service_charge_ids:
            ssc.sudo().unlink()
        service_chg_obj = self.env['tt.service.charge']
        for sc in service_charge_list:
            sc.update({
                'booking_offline_id': self.id,
            })
            if sc['charge_type'] != 'FARE':
                sc.update({
                    'commission_agent_id': sc['agent_id']
                })
            service_chg_obj.create(sc)

    def get_service_charge_summary_airline_train(self, psg, total_passengers):
        vals_list = []
        for rec in self:
            pricing_obj = rec.env['tt.pricing.agent'].search([('agent_type_id', '=', rec.agent_type_id.id),
                                                              ('provider_type_id', '=', rec.provider_type_id.id)],
                                                             limit=1)

            # FARE
            vals = {
                'charge_type': 'FARE',
                'charge_code': 'fare',
                'pax_count': 1,
                'pax_type': psg.pax_type,
                'amount': rec.nta_price / total_passengers,
                'currency': rec.currency_id,
            }
            vals_list.append(vals)

            # RAC
            commission_list = pricing_obj.get_commission(rec.agent_commission, self.agent_id, self.provider_type_id)
            for comm in commission_list:
                comm.update({
                    'charge_type': 'RAC',
                    'charge_code': comm['code'],
                    'currency': rec.currency_id,
                    'pax_type': psg.pax_type,
                    'pax_count': 1
                })
                vals_list.append(comm)

        res = {
            'service_charges': vals_list
        }
        return res

    def get_service_charge_summary_hotel(self, total_line):
        vals_list = []
        for rec in self:
            pricing_obj = rec.env['tt.pricing.agent'].search([('agent_type_id', '=', rec.agent_type_id.id),
                                                              ('provider_type_id', '=', rec.provider_type_id.id)],
                                                             limit=1)

            # FARE
            vals = {
                'charge_type': 'FARE',
                'charge_code': 'fare',
                'pax_count': 1,
                'pax_type': 'ADT',
                'amount': rec.nta_price / total_line,
                'currency': rec.currency_id,
            }
            vals_list.append(vals)

            commission_list = pricing_obj.get_commission(rec.agent_commission, self.agent_id, self.provider_type_id)
            for comm in commission_list:
                comm.update({
                    'charge_type': 'RAC',
                    'charge_code': comm['code'],
                    'currency': rec.currency_id,
                    'pax_type': 'ADT',
                    'pax_count': 1
                })
                vals_list.append(comm)

        res = {
            'service_charges': vals_list
        }
        return res

    def get_service_charge_summary_activity(self):
        vals_list = []
        for rec in self:
            pricing_obj = rec.env['tt.pricing.agent'].search([('agent_type_id', '=', rec.agent_type_id.id),
                                                              ('provider_type_id', '=', rec.provider_type_id.id)],
                                                             limit=1)

    def create_ledger(self, provider_obj):
        for rec in self:
            # Agent Ledger
            pnr = self.get_pnr_list()

            vals = self.env['tt.ledger'].prepare_vals('Resv : ' + rec.name, rec.name, rec.validate_date,
                                                      2, rec.currency_id.id, 0, rec.total_sale_price)
            vals = self.env['tt.ledger'].prepare_vals_for_resv(self, vals)
            vals.update({
                'pnr': pnr,
                'display_provider_name': self.get_display_provider_name(),
                'issued_uid': self.env.user.id,
            })
            new_aml = rec.env['tt.ledger'].create(vals)

    def create_ledger_commission(self, provider_obj):
        for rec in self:
            vals_list = []
            pnr = self.get_pnr_list()

            for ssc in self.sale_service_charge_ids:
                if ssc.charge_type != 'FARE':
                    if ssc.amount > 0:
                        found = False
                        for vals in vals_list:
                            if ssc.commission_agent_id.id == vals['agent_id'] and ssc.charge_code == vals['charge_code']:
                                found = True
                                amount = vals['debit'] + ssc.total
                                vals.update({
                                    'debit': amount
                                })
                        if not found:
                            if ssc.charge_type == 'RAC' or ssc.charge_type == 'rac':
                                # komisi HO
                                if ssc.charge_code == 'hoc':
                                    vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name,
                                                                               'HO: ' + rec.name, rec.validate_date, 3,
                                                                               rec.currency_id.id, ssc.total, 0)

                                    vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                                    vals1.update({
                                        'agent_id': ssc.commission_agent_id.id,
                                        'agent_type_id': ssc.commission_agent_id.agent_type_id.id,
                                        'charge_code': ssc.charge_code,
                                        'pnr': pnr,
                                        'display_provider_name': self.get_display_provider_name(),
                                    })
                                    vals_list.append(vals1)
                                else:
                                    if ssc.charge_code == 'rac':
                                        vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, rec.name,
                                                                                   rec.validate_date, 3,
                                                                                   rec.currency_id.id, ssc.total, 0)
                                        vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                                        vals1.update({
                                            'agent_id': ssc.commission_agent_id.id,
                                            'agent_type_id': ssc.commission_agent_id.agent_type_id.id,
                                            'charge_code': ssc.charge_code,
                                            'pnr': pnr,
                                            'display_provider_name': self.get_display_provider_name(),
                                        })
                                        vals_list.append(vals1)
                                    else:
                                        vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name,
                                                                                   'PA: ' + rec.name,
                                                                                   rec.validate_date, 3,
                                                                                   rec.currency_id.id, ssc.total, 0)
                                        vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                                        vals1.update({
                                            'agent_id': ssc.commission_agent_id.id,
                                            'agent_type_id': ssc.commission_agent_id.agent_type_id.id,
                                            'charge_code': ssc.charge_code,
                                            'pnr': pnr,
                                            'display_provider_name': self.get_display_provider_name(),
                                        })
                                        vals_list.append(vals1)

        for vals in vals_list:
            self.env['tt.ledger'].create(vals)
        print(vals_list)

    def create_final_ho_ledger(self, provider_obj):
        for rec in self:
            # Agent Ledger
            pnr = self.get_pnr_list()

            vals = self.env['tt.ledger'].prepare_vals('Resv : ' + rec.name, 'Profit&Loss: ' + rec.name,
                                                      rec.validate_date, 3, rec.currency_id.id, rec.ho_final_amount, 0)
            vals = self.env['tt.ledger'].prepare_vals_for_resv(self, vals)
            vals.update({
                'pnr': pnr,
                'provider_type_id': self.provider_type_id,
                'display_provider_name': self.get_display_provider_name(),
                'issued_uid': self.env.user.id,
            })
            new_aml = rec.env['tt.ledger'].create(vals)

    def create_reverse_ledger_offline(self):
        provider_obj = self.env['tt.reservation.offline.lines'].search([('booking_id', '=', self.id)])

        try:
            self.sudo().create_reverse_ledger(provider_obj)
            self.sudo().create_reverse_ledger_commission(provider_obj)
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e) + '\nCreate ledger / service charge failed.'
            }

    def create_reverse_ledger(self, provider_obj):
        for rec in self:
            pnr = self.get_pnr_list()

            vals = self.env['tt.ledger'].prepare_vals('Resv : ' + rec.name + ' - REVERSE', rec.name + ' - REVERSE',
                                                      rec.validate_date, 2, rec.currency_id.id, rec.total_sale_price, 0)
            vals = self.env['tt.ledger'].prepare_vals_for_resv(self, vals)
            vals.update({
                'pnr': pnr,
                'reverse_id': self.id,
                'provider_type_id': self.provider_type_id,
                'issued_uid': self.env.user.id,
                'display_provider_name': self.get_display_provider_name()
            })
            new_aml = rec.env['tt.ledger'].create(vals)

    def create_reverse_ledger_commission(self, provider_obj):
        for rec in self:
            vals_list = []
            pnr = self.get_pnr_list()

            for ssc in self.sale_service_charge_ids:
                if ssc.charge_type != 'FARE':
                    if ssc.amount > 0:
                        found = False
                        for vals in vals_list:
                            if ssc.commission_agent_id.id == vals['agent_id'] and ssc.charge_code == vals['charge_code']:
                                found = True
                                amount = vals['credit'] + ssc.total
                                vals.update({
                                    'credit': amount
                                })
                        if not found:
                            if ssc.charge_type == 'RAC' or ssc.charge_type == 'rac':
                                # komisi HO
                                if ssc.charge_code == 'hoc':
                                    vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name,
                                                                               'HO: ' + rec.name + ' - REVERSE',
                                                                               rec.validate_date, 3, rec.currency_id.id,
                                                                               0, ssc.total)

                                    vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                                    vals1.update({
                                        'agent_id': ssc.commission_agent_id.id,
                                        'agent_type_id': ssc.commission_agent_id.agent_type_id.id,
                                        'charge_code': ssc.charge_code,
                                        'pnr': pnr,
                                        'reverse_id': self.id,
                                        'display_provider_name': self.get_display_provider_name(),
                                    })
                                    vals_list.append(vals1)
                                else:
                                    if ssc.charge_code == 'rac':
                                        vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name,
                                                                                   rec.name + ' - REVERSE',
                                                                                   rec.validate_date, 3,
                                                                                   rec.currency_id.id, 0, ssc.total)
                                        vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                                        vals1.update({
                                            'agent_id': ssc.commission_agent_id.id,
                                            'agent_type_id': ssc.commission_agent_id.agent_type_id.id,
                                            'charge_code': ssc.charge_code,
                                            'pnr': pnr,
                                            'reverse_id': self.id,
                                            'display_provider_name': self.get_display_provider_name(),
                                        })
                                        vals_list.append(vals1)
                                    else:
                                        vals1 = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name,
                                                                                   'PA: ' + rec.name + ' - REVERSE',
                                                                                   rec.validate_date, 3,
                                                                                   rec.currency_id.id, 0, ssc.total)
                                        vals1 = self.env['tt.ledger'].prepare_vals_for_resv(self, vals1)
                                        vals1.update({
                                            'agent_id': ssc.commission_agent_id.id,
                                            'agent_type_id': ssc.commission_agent_id.agent_type_id.id,
                                            'charge_code': ssc.charge_code,
                                            'pnr': pnr,
                                            'reverse_id': self.id,
                                            'display_provider_name': self.get_display_provider_name(),
                                        })
                                        vals_list.append(vals1)

        for vals in vals_list:
            self.env['tt.ledger'].create(vals)
        print(vals_list)

    ####################################################################################################

    # Set, Get & Compute

    @api.onchange('agent_commission', 'ho_commission')
    @api.depends('agent_commission', 'ho_commission', 'total_sale_price')
    def _get_nta_price(self):
        for rec in self:
            rec.nta_price = rec.total_sale_price - rec.agent_commission - rec.ho_commission  # - rec.incentive_amount

    @api.onchange('agent_commission')
    @api.depends('agent_commission', 'total_sale_price')
    def _get_agent_price(self):
        for rec in self:
            rec.agent_nta_price = rec.total_sale_price - rec.agent_commission

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
                'agent_id': context['co_agent_id'],
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
                'commercial_agent_id': context['co_agent_id'],
                'agent_id': context['co_agent_id'],
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
                'commercial_agent_id': context['co_agent_id'],
                'agent_id': context['co_agent_id'],
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
                    'commercial_agent_id': context['co_agent_id'],
                    'agent_id': context['co_agent_id'],
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
        print('Agent ID : ' + str(context['co_agent_id']))
        agent_obj = self.env['tt.agent'].search([('id', '=', context['co_agent_id'])])
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
                    'agent_id': context['co_agent_id']
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
                    "room": line.get('room'),
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
                    "activity_package": line.get('package'),
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

    def confirm_api(self, id):
        obj = self.sudo().browse(id)
        obj.action_confirm()
