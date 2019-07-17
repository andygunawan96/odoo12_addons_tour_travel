from odoo import api, fields, models, _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

from .ApiConnector_Hotel import ApiConnectorHotels
API_CN_HOTEL = ApiConnectorHotels()


class HotelReservation(models.Model):
    _name = 'tt.reservation.hotel'
    _description = 'Hotel Reservation'
    _inherit = "tt.reservation"
    _order = 'id DESC'

    # sub_agent_id = fields.Many2one('tt.agent', 'Sub-Agent', readonly=True, states={'draft': [('readonly', False)]},
    #                                help='COR / POR', related='contact_id.agent_id')

    checkin_date = fields.Date('Check In Date', readonly=True, states={'draft': [('readonly', False)]})
    checkout_date = fields.Date('Check Out Date', readonly=True, states={'draft': [('readonly', False)]})
    nights = fields.Integer('Total Nights', default=1)
    room_count = fields.Integer('Room Qty', default=1, readonly=True, states={'draft': [('readonly', False)]})

    # Booking Progress
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Hold Booking'), ('issued', 'Issue'),
                              ('wait', 'Waiting Vendor Validation'), ('refund', 'Refund'), ('fail', 'Failed'),
                              ('cancel', 'Canceled'), ('done', 'Done')], default='draft', help='''
                                  Draft: Draft Reservation; 
                                  Confirm: Hold Reservation; 
                                  Issued: Resv. already paid, Vendor Already confirm the booking; 
                                  Wait: Resv. already paid, Waiting vendor validate booking;
                                  Refund: Refund Ledger (State: Issued= Cancellation Policy, Wait=No CP, Failed=No CP);
                                  Failed: Resv. Failed to Vendor;
                                  Canceled: Resv. Canceled by agent;
                                  Done: Resv. Issued, Person already;
                              ''')
    # provider_booking_ids = fields.One2many('tt.tb.provider.hotel', 'booking_id', string='Provider Booking',
    #                                        readonly=True, states={'draft': [('readonly', False)]})

    # Guests Information

    # Hotel Information
    hotel_id = fields.Many2one('tt.hotel', 'Hotel Information', readonly=True, states={'draft': [('readonly', False)]})
    hotel_name = fields.Char('Hotel Name', readonly=True, states={'draft': [('readonly', False)]})
    hotel_address = fields.Char('Address', readonly=True, states={'draft': [('readonly', False)]})
    hotel_city = fields.Char('City', readonly=True, states={'draft': [('readonly', False)]})
    hotel_city_id = fields.Many2one('res.city', 'City')
    hotel_phone = fields.Char('Phone', readonly=True, states={'draft': [('readonly', False)]})

    # Provider Data & Booking Information
    provider_data = fields.Text('Provider Data', help='Catat Data penting dari provider')
    special_req = fields.Text('Special Request')

    # Invoice & Payment
    sale_service_charge_ids = fields.One2many('tt.service.charge', 'resv_hotel_id', 'Service Charges', ondelete='cascade',
                                              readonly=True, states={'draft': [('readonly', False)]})
    total_supplementary_price = fields.Monetary('Supplementary', compute='_get_total_supplement')
    total_commission_amount = fields.Monetary('Total Commission', readonly=True, compute='_compute_total_cost',
                                              states={'draft': [('readonly', False)]})

    # Agent & Others

    # Booker Information
    # Todo: Email perlu disimpen?
    contact_email = fields.Char('Contact Email', states={'draft': [('readonly', False)]})

    # Cancellation
    cancellation_policy_str = fields.Text('Cancellation Policy')
    sid_issued = fields.Char('SID Issued')
    sid_cancel = fields.Char('SID Cancel')

    # Voucher
    # voucher_name = fields.Char('Voucher', store=True)

    def calc_voucher_name(self):
        for rec in self.search([('state', '=', 'issued')]):
            rec.voucher_name = ''
            for provider in rec.room_detail_ids:
                rec.voucher_name += provider.issued_name and provider.issued_name + '; ' or ''

    @api.multi
    @api.onchange('checkin_date', 'checkout_date')
    def count_days(self):
        for hotel in self:
            if hotel.checkout_date:
                hotel.nights = relativedelta(hotel.checkout_date, hotel.checkin_date).days

    @api.multi
    def get_hotel_name(self):
        for hotel in self:
            if hotel.hotel_id:
                hotel.hotel_name = hotel.hotel_id.name

    @api.onchange('hotel_id')
    @api.depends('hotel_id')
    def get_hotel_name(self):
        for rec in self:
            if rec.hotel_id:
                rec.hotel_name = rec.hotel_id.name
                rec.hotel_address = rec.hotel_id.street
                rec.hotel_city_id = rec.hotel_id.hotel_partner_city_id.id
                rec.hotel_phone = rec.hotel_id.phone

    @api.onchange('hotel_city_id')
    @api.depends('hotel_city_id')
    def get_city_name(self):
        for rec in self:
            if rec.hotel_city_id:
                rec.hotel_city = rec.hotel_city_id.name

    def _compute_total_cost(self):
        for hotel in self:
            hotel.total_commission_amount = 0
            hotel.total = 0
            for detail in hotel.room_detail_ids:
                hotel.total_commission_amount += detail.commission_amount
                hotel.total += detail.sale_price
            hotel.total_nta = hotel.total - hotel.total_commission_amount

    def _compute_total_sale(self):
        total = 0
        for data in self:
            for line in data.room_detail_ids:
                total += line.sale_price * line.qty
            data.total = total

    @api.multi
    def do_print_voucher(self):
        data = {
            'hotel_reservation_id': self.id,
            'form': self.read()
        }
        return self.env["report"].get_action(self, "tt_hotel.report_hotelreservation_ticket", data)

    # @api.depends('room_detail_ids.commission_amount', 'room_detail_ids.qty')
    def _compute_total_commission_amount(self):
        total = 0
        for data in self:
            for line in data.room_detail_ids:
                total += line.commission_amount * line.qty
            data.total_commission_amount = total


    def create_agent_ledger(self, vals):
        # Create Untuk Agent
        # partner = self.create_uid.partner_id.parent_id
        # booker_agent_id = self.customer_id.sudo().agent_id.id
        # user_agent_id = self.agent_id.sudo().parent_agent_id.id
        # vals['agent_id'] = self.get_agent_for_ledger(partner, booker_agent_id, user_agent_id)
        vals['agent_id'] = self.agent_id.id
        new_aml = self.env['tt.ledger'].create(vals)
        return new_aml

    def create_sub_agent_ledger(self, vals):
        # Create Untuk Agent
        # partner = self.sub_agent_id
        # booker_agent_id = self.customer_id.sudo().agent_id.id
        # user_agent_id = self.agent_id.sudo().parent_agent_id.id
        vals['agent_id'] = self.sub_agent_id.id
        new_aml = self.env['tt.ledger'].create(vals)
        return new_aml

    def create_vendor_ledger(self):
        for rec in self.room_detail_ids:
            desc = rec.reservation_id.name
            desc += rec.prov_sale_price and ': (' + str(rec.prov_sale_price) + ' ' or '('
            desc += rec.prov_currency_id and rec.prov_currency_id.name + ')' or ')'
            rate_obj = rec.provider_id.find_rate(str(fields.Date.today()), rec.prov_currency_id.id)
            desc += rate_obj and ' Rate: ' + str(rate_obj.buy_rate) or ''
            self.env['tt.provider.ledger'].sudo().create({
                'description': desc,
                'vendor_id': rec.provider_id.id,
                'rate_id': rate_obj and rate_obj.id or False,
                'debit': 0,
                'credit': rate_obj and rate_obj.buy_rate * rec.prov_sale_price or rec.prov_sale_price,
            })
        return True

    @api.multi
    def create_ledger(self):
        for rec in self:
            vals = self.env['tt.ledger'].prepare_vals('Resv : '+ rec.name, rec.name, rec.issued_date, 'hotel', rec.currency_id.id, 0, rec.total)
            vals['hotel_reservation_id'] = rec.id
            new_aml = rec.create_agent_ledger(vals)
            new_aml.action_done()
            rec.ledger_id = new_aml
            # Create Commission
            vals = self.env['tt.ledger'].prepare_vals('Commission : ' + rec.name, rec.name, rec.issued_date, 'hotel',
                                                      rec.currency_id.id, rec.total_commission_amount, 0)
            commission_aml = rec.create_agent_ledger(vals)
            commission_aml.action_done()
            rec.commission_ledger_id = commission_aml
            # if self.agent_id != self.sub_agent_id:
            #     new_aml = rec.create_sub_agent_ledger(vals)
            #     new_aml.action_done()
            #     rec.sub_ledger_id = new_aml

    @api.multi
    def _refund_ledger(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            vals = ledger.prepare_vals('Resv : ' + rec.name, rec.name, rec.issued_date, 'hotel', rec.currency_id.id, rec.total,
                                       0)
            vals['hotel_reservation_id'] = rec.id
            vals['agent_id'] = rec.agent_id.id
            new_aml = ledger.create(vals)
            new_aml.action_done()
            rec.ledger_id = new_aml

    @api.one
    def action_confirm(self, kwargs=False):
        self.state = 'confirm'
        self.confirm_date = fields.Datetime.now()
        self.confirm_uid = kwargs and kwargs.get('user_id', self.env.user.id) or self.env.user.id
        self.name = self.name == 'New' and self.env['ir.sequence'].next_by_code('tt.reservation.hotel') or self.name

    @api.one
    def action_booked(self):
        self.state = 'approved'
        self.book_date = fields.Date.today()
        self.env['test.search'].validation_booking(self.id)
        return True

    @api.one
    def action_refund(self):
        # Todo Tambahkan pengecekan state disini
        self.state = 'refund'
        self._refund_ledger()

    @api.one
    def action_draft(self):
        self.state = 'draft'

    def create_agent_invoice(self):
        return True

    @api.one
    def action_issued_backend(self):
        is_enough = self.action_issued()
        if is_enough[0]['error_code'] != 0:
            raise UserError(is_enough[0]['error_msg'])

    def action_failed(self, msg=''):
        self.state='fail'
        self.fail_message= msg
        return True

    @api.one
    def action_set_to_issued(self, kwargs=False):
        self.state = 'issued'

    @api.one
    def action_set_to_failed(self, kwargs=False):
        self.state = 'fail'

    @api.one
    def action_issued(self, kwargs=False):
        # 1. Ledger
        is_enough = self.env['res.partner'].check_balance_limit(self.sub_agent_id.id, self.total)
        if is_enough['error_code'] == 0:
            # Jika cukup Potong Saldo
            self.issued_date = fields.Datetime.now()
            self.issued_uid = kwargs and kwargs.get('user_id') and kwargs['user_id'] or self.env.user.id
            # 1. Create Ledger, Commission Ledger
            self.sudo().create_ledger()
            self.sudo().create_vendor_ledger()
            # 2. Jika Hotel CMS apakah kamar yg dipesan auto validation / perlu operator
            # self.check_auto_approved()
            # TODO 3. Kirim E-Ticket
            self.create_agent_invoice()
            self.state = 'issued'
            self.calc_voucher_name()
        return is_enough

    @api.one
    def action_done(self):
        self.state = 'done'

    def _prepare_invoice(self):
        a = {
            'payment_term_id': 2,
            'partner_id': self.customer_id.id or self.agent_id.id,
            'resv_id': self.id,
            'name': self.name,
        }
        return a

    @api.multi
    def action_ticket_customer(self):
        vals = self._prepare_invoice()
        vals.update({
            'resv_type': 'cust',
        })
        inv_id = self.env['account.invoice'].create(vals)

        # Jika Dibuat per kamar per malam
        hotel_name = self.hotel_id.name or ''
        for line in self.room_detail_ids:
            value_line = {
                'invoice_id': inv_id.id,
                'name': hotel_name + " " + line.room_info_id.name,
                'account_id': 17,
                'qty': 1,
                'price_unit': line.sale_price,
                'commission_amount': line.commission_amount,
                'no_ticket': line.id
            }
            self.env['account.invoice.line'].create(value_line)

        # Jika Dibuat keseluruhan total
        # value_line = {
        #     'invoice_id': inv_id.id,
        #     'name': self.hotel_id.name + " " + self.checkin_date + " " + self.checkout_date,
        #     'account_id': 17,
        #     'qty': 1,
        #     'price_unit': self.total,
        #     'commission_amount': self.total_commission_amount,
        #     'no_ticket': self.number
        # }
        # self.env['account.invoice.line'].create(value_line)

        # form_id = self.env.ref('tt_hotel.tt_hotel_reservation_detail_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.invoice',
            'res_id': inv_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            # 'view_id': form_id.id,
            'context': {},
            # if you want to open the form in edit mode direclty
            # 'flags': {'initial_mode': 'edit'},
            'target': 'current',
        }

    @api.multi
    def action_ticket_agent(self):
        vals = self._prepare_invoice()
        vals.update({
            'resv_type': 'agent',
            'reference': self.name,
        })
        inv_id = self.env['account.invoice'].create(vals)

        # Jika Dibuat per kamar per malam
        # for line in self.room_detail_ids:
        #     value_line = {
        #         'invoice_id': inv_id.id,
        #         'name': self.hotel_id.name + " " + line.room_info_id.name,
        #         'account_id': 17,
        #         'qty': 1,
        #         'price_unit': line.sale_price,
        #         'commission_amount': line.commission_amount,
        #         'no_ticket': line.id
        #     }
        #     self.env['account.invoice.line'].create(value_line)

        # Jika Dibuat keseluruhan total
        hotel_name = self.hotel_id.name or ''
        value_line = {
            'invoice_id': inv_id.id,
            'name': hotel_name + " " + self.checkin_date + " " + self.checkout_date,
            'account_id': 17,
            'qty': 1,
            'price_unit': self.total,
            'commission_amount': self.total_commission_amount,
            'no_ticket': self.number
        }
        self.env['account.invoice.line'].create(value_line)

        # form_id = self.env.ref('tt_hotel.tt_hotel_reservation_detail_form')
        self.action_issued()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.invoice',
            'res_id': inv_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            # 'view_id': form_id.id,
            'context': {},
            # if you want to open the form in edit mode direclty
            # 'flags': {'initial_mode': 'edit'},
            'target': 'current',
        }

    @api.multi
    def action_ticket_vendor(self):
        vals = self._prepare_invoice()
        vals.update({
            'type': 'in_invoice',
            'resv_type': 'vendor',
            'reference': self.number,
            'journal_id': self.env['account.journal'].search([('type', '=', 'sale')])[0].id
        })
        inv_id = self.env['account.invoice'].create(vals)

        # Jika Dibuat per kamar per malam
        # for line in self.room_detail_ids:
        #     value_line = {
        #         'invoice_id': inv_id.id,
        #         'name': self.hotel_id.name + " " + line.room_info_id.name,
        #         'account_id': 17,
        #         'qty': 1,
        #         'price_unit': line.sale_price - line.commission_amount,
        #         'commission_amount': 0,
        #         'no_ticket': line.id
        #     }
        #     self.env['account.invoice.line'].create(value_line)

        # Jika Dibuat keseluruhan total
        price_unit = 0
        commission = 0
        for line in self.room_detail_ids.filtered(lambda x: x.payment_method == 'cash'):
            price_unit += line.sale_price - line.commission_amount
            commission += line.commission_amount
        hotel_name = self.hotel_id.name or ''
        value_line = {
            'invoice_id': inv_id.id,
            'name': hotel_name + " " + self.checkin_date + " " + self.checkout_date,
            'account_id': 17,
            'qty': 1,
            'price_unit': price_unit,
            'commission_amount': commission,
            'no_ticket': self.number
        }
        self.env['account.invoice.line'].create(value_line)
        self.action_done()
        form_id = self.env.ref('account.invoice_supplier_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.invoice',
            'res_id': inv_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            # if you want to open the form in edit mode direclty
            # 'flags': {'initial_mode': 'edit'},
            'target': 'current',
        }

    def get_agent_for_ledger(self, partner, booker_agent_id, user_agent_id):
        agent_id = False
        if partner:
            if partner.is_HO:
                agent_id = booker_agent_id.id
            elif partner.agent_type_id.id in self.env.user.allowed_customer_ids.ids:
                agent_id = user_agent_id
            else:
                agent_id = partner.id
        return agent_id

    def get_subagent_for_ledger(self, partner, booker_agent_id, user_agent_id):
        agent_id = False
        if partner:
            if partner.is_HO:
                agent_id = booker_agent_id
            else:
                agent_id = partner.id
        return agent_id

    @api.multi
    def action_send_email(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('tt_transport_printout', 'email_template_rodex')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        template_name = []
        template_name.append('kai')

        data = {
            'booking_id': self.id,
            'invoicing': 0,
            'carriers': template_name
        }
        ctx = dict()
        ctx.update({
            'default_model': 'tt.transport.booking',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id.id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "tt_transport_printout.mail_template_data_notification_email_rodex",
            'data': data
        })

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.depends('supplementary_ids.qty', 'supplementary_ids.sale_price')
    def _get_total_supplement(self):
        for my in self:
            total = 0
            for suplement_id in my.supplementary_ids:
                total += suplement_id.qty * suplement_id.sale_price
            my.total_supplementary_price = total
        return 0

    def check_booking_status(self):
        api_context = {
            'co_uid': self.env.user.agent_id.id
        }
        res = API_CN_HOTEL.check_booking_status_by_api({'name': self.name, 'issued_name': self.room_detail_ids[0].issued_name, 'provider': self.room_detail_ids[0].provider_id.provider_code}, api_context)
        if res['error_code'] != 0:
            raise ('Error')
        else:
            return True

    def check_booking_policy(self):
        api_context = {
            'co_uid': self.env.user.agent_id.id
        }
        res = API_CN_HOTEL.check_booking_policy_by_api({'name': self.name, 'issued_name': self.room_detail_ids[0].issued_name,
                                                        'provider': self.room_detail_ids[0].provider_id.provider_code
                                                        }, api_context)
        if res['error_code'] != 0:
            raise ('Error')
        else:
            return True

    def cancel_booking(self):
        api_context = {
            'co_uid': self.env.user.agent_id.id
        }
        res = API_CN_HOTEL.cancel_booking_by_api({
            'name': self.name,
            'issued_name': self.room_detail_ids[0].issued_name,
            'provider': self.room_detail_ids[0].provider_id.provider_code
        }, api_context)
        if res['error_code'] != 0:
            raise ('Error')
        else:
            return True


class ServiceCharge(models.Model):
    _inherit = "tt.service.charge"

    provider_hotel_booking_id = fields.Many2one('tt.tb.provider.hotel', 'Provider Booking ID')
    resv_hotel_id = fields.Many2one('tt.reservation.hotel', 'Hotel', ondelete='cascade', index=True, copy=False)
