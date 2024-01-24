from odoo import api,models,fields,_
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from ...tools import variables
import base64,pytz
from ...tools.ERR import RequestException
from ...tools import util,ERR
import logging,traceback
import json

_logger = logging.getLogger(__name__)


class TtRefundLine(models.Model):
    _name = "tt.refund.line"
    _description = "Refund Line Model"

    name = fields.Char('Name', readonly=True)
    birth_date = fields.Date('Birth Date', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    pax_price = fields.Monetary('Passenger Price', default=0, readonly=True)
    charge_fee = fields.Monetary('Charge Fee', default=0, readonly=True, states={'confirm': [('readonly', False)]})
    commission_fee = fields.Monetary('Commission Fee', default=0, readonly=True, states={'confirm': [('readonly', False)]})
    refund_amount = fields.Monetary('Expected Refund Amount', default=0, required=True, readonly=True, compute='_compute_refund_amount')
    real_refund_amount = fields.Monetary('Real Refund Amount', default=0, readonly=False, states={'draft': [('readonly', True)]})
    extra_charge_amount = fields.Monetary('Extra Charge Fee', default=0, readonly=True, states={'finalize': [('readonly', False)]})
    refund_id = fields.Many2one('tt.refund', 'Refund', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('sent', 'Sent'), ('finalize', 'Finalized'), ('done', 'Done')], 'State', default='draft', related='')
    total_vendor = fields.Integer('Total Vendor')

    @api.multi
    def write(self, vals):
        if vals.get('extra_charge_amount'):
            if vals['extra_charge_amount'] > self.refund_amount:
                raise UserError(_('Extra charge fee cannot be higher than the expected refund amount!'))
        return super(TtRefundLine, self).write(vals)

    def to_dict(self):
        res = {
            'name': self.name,
            'birth_date': self.birth_date and self.birth_date.strftime('%Y-%m-%d') or '',
            'currency': self.currency_id.name,
            'pax_price': self.pax_price,
            'charge_fee': self.charge_fee,
            'commission_fee': self.commission_fee,
            'refund_amount': self.refund_amount,
        }
        return res

    @api.depends('pax_price', 'charge_fee', 'commission_fee')
    @api.onchange('pax_price', 'charge_fee', 'commission_fee')
    def _compute_refund_amount(self):
        for rec in self:
            rec.refund_amount = rec.pax_price - (rec.charge_fee + rec.commission_fee)

    def set_to_draft(self):
        self.write({
            'state': 'draft',
        })

    def set_to_confirm(self):
        # tanya boleh tidak IVAN
        self.commission_fee = 0
        self.charge_fee = 0
        self.write({
            'state': 'confirm',
        })

    def set_to_sent(self):
        self.write({
            'state': 'sent',
        })

    def set_to_finalize(self):
        self.write({
            'state': 'finalize',
        })

    def set_to_done(self):
        self.write({
            'state': 'done',
        })


class TtRefundLineCustomer(models.Model):
    _name = "tt.refund.line.customer"
    _description = "Refund Line Customer Model"

    name = fields.Char('Name', readonly=True)
    birth_date = fields.Date('Birth Date', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    method = fields.Selection([('validation', 'Validation of the bank card'), ('server2server', 'Server To Server'),
                               ('form', 'Form'), ('form_save', 'Form with tokenization')], 'Method', related='acquirer_id.type', readonly=True)
    bank_id = fields.Many2one('tt.bank', 'To Bank')
    refund_amount = fields.Monetary('Refund Amount', default=0, readonly=True)
    citra_fee = fields.Monetary('Additional Fee', default=0, readonly=False)
    total_amount = fields.Monetary('Total Amount', default=0, required=True, readonly=True, compute='_compute_total_amount')
    refund_id = fields.Many2one('tt.refund', 'Refund', readonly=True)
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], related='refund_id.ho_id')
    agent_id = fields.Many2one('tt.agent', 'Agent', related='refund_id.agent_id')
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id', readonly=True)
    acquirer_id = fields.Many2one('payment.acquirer', 'Payment Acquirer', domain="[('agent_id','=',agent_id)]")
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('sent', 'Sent'), ('validate', 'Validated'), ('final', 'Finalization'),
                              ('approve', 'Approved'), ('payment', 'Payment'),
                              ('approve_cust', 'Approved (Cust. Payment)'), ('done', 'Done'), ('cancel', 'Canceled'),
                              ('expired', 'Expired')], 'Status', default='draft', related='refund_id.state')

    def to_dict(self):
        res = {
            'name': self.name,
            'birth_date': self.birth_date and self.birth_date.strftime('%Y-%m-%d') or '',
            'currency': self.currency_id.name,
            'refund_amount': self.refund_amount,
            'admin_fee': self.citra_fee,
            'total_amount': self.total_amount,
            'payment_acquirer': self.acquirer_id and {
                'seq_id': self.acquirer_id.seq_id or '',
                'name': self.acquirer_id.name or '',
                'accounting_name': self.acquirer_id.jasaweb_name or '',
                'account_number': self.acquirer_id.account_number or '',
                'account_name': self.acquirer_id.account_name or '',
                'bank': self.acquirer_id.bank_id and self.acquirer_id.bank_id.name or ''
            } or {}
        }
        return res

    @api.depends('refund_amount', 'citra_fee')
    @api.onchange('refund_amount', 'citra_fee')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.refund_amount - rec.citra_fee


class TtRefund(models.Model):
    _name = "tt.refund"
    _inherit = 'tt.history'
    _description = "Refund Model"
    _order = 'id DESC'

    name = fields.Char('Name', readonly=True, default='New', copy=False)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('sent', 'Sent'), ('validate', 'Validated'), ('final', 'Finalization'), ('approve', 'Approved'), ('payment', 'Payment'),
                              ('approve_cust', 'Approved (Cust. Payment)'), ('done', 'Done'), ('cancel', 'Canceled'), ('expired', 'Expired')], 'Status', default='draft',
                             help=" * The 'Draft' status is used for Agent to make refund request.\n"
                                  " * The 'Confirmed' status is used for HO to confirm and process the request.\n"
                                  " * The 'Sent' status is used for HO to send the request back to Agent with a set refund amount.\n"
                                  " * The 'Validated' status is used for Agent to final check and validate the request.\n"
                                  " * The 'Finalization' status is used for HO to finalize and process the request.\n"
                                  " * The 'Approved' status means the agent's balance has been refunded, either by system CRON or forced by HO.\n"
                                  " * The 'Payment' status is used for Agent to upsell the request.\n"
                                  " * The 'Approved (Cust. Payment)' status means the agent upsell has been approved by agent manager.\n"
                                  " * The 'Done' status means the request has been done.\n"
                                  " * The 'Canceled' status is used for Agent or HO to cancel the request.\n"
                                  " * The 'Expired' status means the request has been expired.\n")

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True,
                               default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True,
                               default=lambda self: self.env.user.agent_id)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True, store=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                              store=True, readonly=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    refund_date = fields.Date('Expected Refund Date', default=date.today(), required=True, readonly=True, related='refund_date_ho')
    refund_date_ho = fields.Date('Expected Refund Date', default=date.today(), required=False, readonly=True, states={'confirm': [('readonly', False), ('required', True)]})
    real_refund_date = fields.Date('Real Refund Date from Vendor', default=date.today(), required=True, readonly=False, states={'done': [('readonly', True)], 'approve': [('readonly', True)], 'draft': [('readonly', True)]})
    cust_refund_date = fields.Date('Expected Cust. Refund Date', readonly=False, states={'done': [('readonly', True)]})

    service_type = fields.Selection(lambda self: self.get_service_type(), 'Service Type', required=True, readonly=True)
    refund_type_id = fields.Many2one('tt.refund.type', 'Refund Type', required=False, readonly=True, states={'draft': [('readonly', False)]})

    def get_admin_fee_domain(self):
        agent_type_adm_ids = self.agent_id.agent_type_id.admin_fee_ids.ids
        agent_adm_ids = self.agent_id.admin_fee_ids.ids
        return [('after_sales_type', '=', 'refund'), ('ho_id', '=', self.ho_id.id), '&', '|',
                ('agent_type_access_type', '=', 'all'), '|', '&', ('agent_type_access_type', '=', 'allow'),
                ('id', 'in', agent_type_adm_ids), '&', ('agent_type_access_type', '=', 'restrict'),
                ('id', 'not in', agent_type_adm_ids), '|', ('agent_access_type', '=', 'all'), '|', '&',
                ('agent_access_type', '=', 'allow'), ('id', 'in', agent_adm_ids), '&',
                ('agent_access_type', '=', 'restrict'), ('id', 'not in', agent_adm_ids)]

    admin_fee_id = fields.Many2one('tt.master.admin.fee', 'Admin Fee Type', domain=get_admin_fee_domain, readonly=True)
    admin_fee = fields.Monetary('Total Admin Fee', default=0, readonly=True, compute="_compute_admin_fee", store=True)
    admin_fee_ho = fields.Monetary('Admin Fee (HO)', default=0, readonly=True, compute="_compute_admin_fee", store=True)
    admin_fee_agent = fields.Monetary('Admin Fee (Agent)', default=0, readonly=True, compute="_compute_admin_fee", store=True)
    refund_amount = fields.Monetary('Expected Refund Amount', default=0, required=True, readonly=True, compute='_compute_refund_amount', store=True)
    real_refund_amount = fields.Monetary('Real Refund Amount from Vendor', default=0, readonly=True, compute='_compute_real_refund_amount')
    total_amount = fields.Monetary('Total Amount', default=0, readonly=True, compute="_compute_total_amount", store=True)
    total_amount_cust = fields.Monetary('Total Amount (Customer)', default=0, readonly=True, compute="_compute_total_amount_cust", store=True)
    final_admin_fee = fields.Monetary('Admin Fee Amount', default=0, readonly=True)
    final_admin_fee_ho = fields.Monetary('Admin Fee Amount (HO)', default=0, readonly=True)
    final_admin_fee_agent = fields.Monetary('Admin Fee Amount (Agent)', default=0, readonly=True)
    booking_desc = fields.Html('Booking Description', readonly=True)
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    refund_line_ids = fields.One2many('tt.refund.line', 'refund_id', 'Refund Line(s)', readonly=False)
    refund_line_cust_ids = fields.One2many('tt.refund.line.customer', 'refund_id', 'Payment to Customer(s)', readonly=True, states={'payment': [('readonly', False)]})

    referenced_pnr = fields.Char('Ref. PNR', readonly=True)
    referenced_document = fields.Char('Ref. Document', readonly=True)

    referenced_document_external = fields.Char('Ref. External Document', readonly=True) #jika btbo2

    res_model = fields.Char('Related Reservation Name', index=True, readonly=True)

    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    profit_loss_created = fields.Boolean('Profit & Loss Created', default=False, readonly=True)
    is_vendor_received = fields.Boolean('Refund Received from Vendor', default=False, readonly=True, states={'final': [('readonly', False)]})

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]

    ledger_ids = fields.One2many('tt.ledger','refund_id')
    adjustment_ids = fields.One2many('tt.adjustment', 'res_id', 'Adjustment', readonly=True, domain=_get_res_model_domain)

    hold_date = fields.Datetime('Hold Date', readonly=True)
    confirm_date = fields.Datetime('Confirm Date', readonly=True)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    sent_date = fields.Datetime('Sent Date', readonly=True)
    sent_uid = fields.Many2one('res.users', 'Sent by', readonly=True)
    validate_date = fields.Datetime('Validate Date', readonly=True)
    validate_uid = fields.Many2one('res.users', 'Validated by', readonly=True)
    final_date = fields.Datetime('Finalized Date', readonly=True)
    final_uid = fields.Many2one('res.users', 'Finalized by', readonly=True)
    approve_date = fields.Datetime('Approved Date', readonly=True)
    approve_uid = fields.Many2one('res.users', 'Approved by', readonly=True)
    payment_date = fields.Datetime('Set to Payment Date', readonly=True)
    payment_uid = fields.Many2one('res.users', 'Set to Payment by', readonly=True)
    approve2_date = fields.Datetime('Agent Approved Date', readonly=True)
    approve2_uid = fields.Many2one('res.users', 'Agent Approved by', readonly=True)
    done_date = fields.Datetime('Done Date', readonly=True)
    done_uid = fields.Many2one('res.users', 'Done by', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Canceled by', readonly=True)
    cancel_date = fields.Datetime('Cancel Date', readonly=True)
    cancel_message = fields.Text('Cancelation Message', required=False, readonly=True, states={'validate': [('readonly', False)], 'final': [('readonly', False)], 'done': [('readonly', False)]})

    printout_refund_ho_id = fields.Many2one('tt.upload.center', 'Refund Printout HO', readonly=True)
    printout_refund_ho_cust_id = fields.Many2one('tt.upload.center', 'Refund Printout HO Cust', readonly=True)
    printout_refund_id = fields.Many2one('tt.upload.center', 'Refund Printout', readonly=True)
    printout_refund_est_id = fields.Many2one('tt.upload.center', 'Refund Printout Est', readonly=True)

    created_by_api = fields.Boolean('Created By API', default=False, readonly=True)

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code(self._name)
        if 'service_type' in vals_list:
            vals_list['service_type'] = self.parse_service_type(vals_list['service_type'])
        if not self.env.user.has_group('tt_base.group_after_sales_master_level_3') and vals_list.get('state') == 'final':
            vals_list.pop('state')
        if not self.env.user.has_group('tt_base.group_after_sales_master_level_5') and vals_list.get('is_vendor_received'):
            vals_list.pop('is_vendor_received')

        return super(TtRefund, self).create(vals_list)

    @api.multi
    def write(self, vals_list):
        if not self.env.user.has_group('tt_base.group_after_sales_master_level_3') and vals_list.get('state') == 'final':
            vals_list.pop('state')
        if not self.env.user.has_group('tt_base.group_after_sales_master_level_5') and vals_list.get('is_vendor_received'):
            vals_list.pop('is_vendor_received')
        return super(TtRefund, self).write(vals_list)

    def to_dict(self):
        return {
            'order_number': self.name,
            'refund_type': self.refund_type_id.name if self.refund_type_id else '',
            'ho_id': self.ho_id.id if self.ho_id else '',
            'agent_id': self.agent_id.id if self.agent_id else '',
            'referenced_pnr': self.referenced_pnr,
            'referenced_document': self.referenced_document,
            'state': self.state,
            'booker': self.booker_id.to_dict(),
            'currency': self.currency_id.name if self.currency_id else '',
            'refund_amount': self.refund_amount or 0,
            'real_refund_amount': self.real_refund_amount or 0,
            'admin_fee_type': self.admin_fee_id.name if self.admin_fee_id else '',
            'admin_fee': self.admin_fee or 0,
            'total_amount': self.total_amount or 0,
            'refund_date': self.refund_date and self.refund_date.strftime('%Y-%m-%d') or '',
            'real_refund_date': self.real_refund_date and self.real_refund_date.strftime('%Y-%m-%d') or '',
            'refund_lines': [line.to_dict() for line in self.refund_line_ids],
            'refund_to_cust_lines': [line_cust.to_dict() for line_cust in self.refund_line_cust_ids]
        }

    @api.depends('refund_line_ids')
    @api.onchange('refund_line_ids')
    def _compute_refund_amount(self):
        for rec in self:
            temp_total = 0
            for rec2 in rec.refund_line_ids:
                temp_total += rec2.refund_amount - rec2.extra_charge_amount
            rec.refund_amount = temp_total

    @api.depends('refund_line_ids')
    @api.onchange('refund_line_ids')
    def _compute_real_refund_amount(self):
        for rec in self:
            temp_total = 0
            for rec2 in rec.refund_line_ids:
                temp_total += rec2.real_refund_amount
            rec.real_refund_amount = temp_total

    def get_refund_admin_fee_rule(self, agent_id, refund_type='regular', ho_id=False):
        search_param = [('after_sales_type', '=', 'refund')]
        if refund_type == 'quick':
            default_refund_type_id = self.env.ref('tt_accounting.refund_type_quick_refund').id
            default_adm_fee_name = 'Quick Refund'
            default_amt_type = 'percentage'
            default_amt = 5
        else:
            default_refund_type_id = self.env.ref('tt_accounting.refund_type_regular_refund').id
            default_adm_fee_name = 'Regular Refund'
            default_amt_type = 'amount'
            default_amt = 50000
        search_param.append(('refund_type_id', '=', default_refund_type_id))
        agent_obj = self.env['tt.agent'].browse(int(agent_id))
        if ho_id:
            ho_obj = self.env['tt.agent'].browse(int(ho_id))
        else:
            ho_obj = agent_obj and agent_obj.ho_id or False
        if ho_obj:
            search_param.append(('ho_id', '=', ho_obj.id))
        refund_admin_fee_list = self.env['tt.master.admin.fee'].search(search_param, order='sequence, id desc')
        if refund_admin_fee_list:
            qualified_admin_fee = []
            for admin_fee in refund_admin_fee_list:
                is_agent = False
                is_agent_type = False
                if admin_fee.agent_access_type == 'all':
                    is_agent = True
                elif admin_fee.agent_access_type == 'allow' and agent_id in admin_fee.agent_ids.ids:
                    is_agent = True
                elif admin_fee.agent_access_type == 'restrict' and agent_id not in admin_fee.agent_ids.ids:
                    is_agent = True

                if admin_fee.agent_type_access_type == 'all':
                    is_agent_type = True
                elif admin_fee.agent_type_access_type == 'allow' and agent_obj.agent_type_id.id in admin_fee.agent_type_ids.ids:
                    is_agent_type = True
                elif admin_fee.agent_type_access_type == 'restrict' and agent_obj.agent_type_id.id not in admin_fee.agent_type_ids.ids:
                    is_agent_type = True

                if not is_agent_type or not is_agent:
                    continue

                qualified_admin_fee.append(admin_fee)
            current_refund_env = qualified_admin_fee and qualified_admin_fee[0] or False
        else:
            current_refund_env = False
        if not current_refund_env:
            current_refund_env = self.env['tt.master.admin.fee'].create({
                'name': default_adm_fee_name,
                'after_sales_type': 'refund',
                'refund_type_id': default_refund_type_id,
                'min_amount_ho': 0,
                'min_amount_agent': 0,
                'agent_type_access_type': 'all',
                'agent_access_type': 'all',
                'ho_id': ho_obj and ho_obj.id or self.env.ref('tt_base.rodex_ho').id,
                'sequence': 500
            })
            self.env['tt.master.admin.fee.line'].create({
                'type': default_amt_type,
                'amount': default_amt,
                'is_per_pnr': True,
                'is_per_pax': True,
                'balance_for': 'ho',
                'master_admin_fee_id': current_refund_env.id
            })
        return current_refund_env

    def get_refund_fee_amount(self, agent_id, order_number='', order_type='', refund_amount=0, passenger_count=0, refund_type='regular'):
        admin_fee_obj = self.get_refund_admin_fee_rule(agent_id, refund_type)

        pnr_amount = 1
        pax_amount = 1
        journey_amount = 1
        if order_number and order_type:
            book_obj = self.env['tt.reservation.'+order_type].search([('name', '=', order_number)], limit=1)

            pnr_amount = len(book_obj.provider_booking_ids.ids)
            pax_amount = int(passenger_count) or len(book_obj.passenger_ids.ids)
            if order_type == 'airline':
                journey_amount = 0
                for rec in book_obj.provider_booking_ids:
                    for rec2 in rec.journey_ids:
                        journey_amount += 1

        admin_fee_ho = admin_fee_obj.get_final_adm_fee_ho(refund_amount, pnr_amount, pax_amount, journey_amount)
        admin_fee_agent = admin_fee_obj.get_final_adm_fee_agent(refund_amount, pnr_amount, pax_amount, journey_amount)
        admin_fee = admin_fee_ho + admin_fee_agent
        return {
            'admin_fee_ho': admin_fee_ho,
            'admin_fee_agent': admin_fee_agent,
            'admin_fee': admin_fee,
        }

    # temporary function
    def compute_all_admin_fee(self):
        all_refunds = self.search([])
        for rec in all_refunds:
            rec._compute_admin_fee()

    def recalculate_admin_fee(self):
        self._compute_admin_fee()

    @api.depends('admin_fee_id', 'refund_amount', 'res_model', 'res_id')
    @api.onchange('admin_fee_id', 'refund_amount', 'res_model', 'res_id')
    def _compute_admin_fee(self):
        for rec in self:
            if rec.admin_fee_id and rec.res_model and rec.res_id:
                try:
                    book_obj = self.env[rec.res_model].browse(int(rec.res_id))
                    pnr_amount = 0
                    journey_amount = 0
                    for rec2 in book_obj.provider_booking_ids:
                        pnr_amount += 1
                        if rec.res_model == 'tt.reservation.airline':
                            for rec3 in rec2.journey_ids:
                                journey_amount += 1
                        else:
                            journey_amount = 1

                    pax_amount = 0
                    for rec2 in book_obj.passenger_ids:
                        pax_amount += 1

                    rec.admin_fee_ho = rec.admin_fee_id.get_final_adm_fee_ho(rec.refund_amount, pnr_amount, pax_amount, journey_amount)
                    rec.admin_fee_agent = rec.admin_fee_id.get_final_adm_fee_agent(rec.refund_amount, pnr_amount, pax_amount, journey_amount)
                    rec.admin_fee = rec.admin_fee_ho + rec.admin_fee_agent
                except:
                    rec.admin_fee_ho = rec.admin_fee_ho and rec.admin_fee_ho or 0
                    rec.admin_fee_agent = rec.admin_fee_agent and rec.admin_fee_agent or 0
                    rec.admin_fee = rec.admin_fee and rec.admin_fee or 0
            else:
                rec.admin_fee_ho = 0
                rec.admin_fee_agent = 0
                rec.admin_fee = 0

    def compute_admin_fee_api(self, req):
        refund_fee = self.get_refund_fee_amount(req['agent_id'], req['order_number'], req['order_type'], req['refund_amount'], req.get('passenger_count'), req.get('refund_type'))
        return refund_fee['admin_fee']

    @api.depends('admin_fee', 'refund_amount')
    @api.onchange('admin_fee', 'refund_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.refund_amount - rec.admin_fee

    @api.depends('refund_line_cust_ids')
    @api.onchange('refund_line_cust_ids')
    def _compute_total_amount_cust(self):
        for rec in self:
            cust_total = 0
            for rec2 in rec.refund_line_cust_ids:
                cust_total += rec2.total_amount
            rec.total_amount_cust = cust_total

    def parse_service_type(self,type):
        return self.env['tt.provider.type'].browse(int(type)).code

    def get_service_type(self):
        return [(rec,rec.capitalize()) for rec in self.env['tt.provider.type'].get_provider_type()]

    def get_company_name(self):
        company_obj = self.env['res.company'].search([], limit=1)
        return company_obj.name

    def action_expired(self):
        self.write({
            'state': 'expired',
        })

    def set_to_confirm_api(self, data, ctx):
        try:
            refund_obj = self.search([('referenced_document', '=', data['referenced_document_external']),('state','=', data['state'])], limit=1)
            if refund_obj:
                refund_obj.set_to_confirm()
                res = ERR.get_no_error()
            else:
                res = ERR.get_error(500)
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(500, additional_message='refund not found')
        return res

    def set_to_confirm(self):
        # jika ada provider rodextrip untuk BTBO2 IVAN
        resv_obj = self.env[self.res_model].search([('name', '=', self.referenced_document)])
        for rec in resv_obj.provider_booking_ids:
            if 'rodextrip' in rec.provider_id.code:
                # tembak gateway
                data = {
                    # 'referenced_document_external': 'AL.20120301695',
                    'referenced_document_external': rec.get('pnr2') or '',
                    'res_model': self.res_model,
                    'provider': rec.provider_id.code,
                    'state': self.state,
                    'type': 'set_to_confirm'
                }
                self.env['tt.refund.api.con'].send_refund_request(data, self.agent_id.ho_id.id)

        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
            'hold_date': False
        })

        for rec in self.refund_line_ids:
            rec.set_to_confirm()

    def refund_confirm_api(self, data, ctx):
        try:
            refund_obj = self.search([('referenced_document', '=', data['referenced_document_external']),('state','=','draft')], limit=1)
            if refund_obj:
                refund_obj.confirm_refund_from_button()
                res = ERR.get_no_error()
            else:
                res = ERR.get_error(500)
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(500, additional_message='refund not found')
        return res

    def confirm_refund_from_button(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('tt_base.group_tt_corpor_user').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 6')
        if self.state != 'draft':
            raise UserError("Cannot Confirm because state is not 'draft'.")

        estimate_refund_date = date.today() + relativedelta(days=self.refund_type_id.days)

        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
            'refund_date_ho': estimate_refund_date,
        })
        for rec in self.refund_line_ids:
            rec.set_to_confirm()

        try:
            mail_created = self.env['tt.email.queue'].sudo().search(
                [('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'refund_confirmed')],
                limit=1)
            if not mail_created:
                temp_data = {
                    'provider_type': 'refund',
                    'order_number': self.name,
                    'type': 'confirmed',
                }
                temp_context = {
                    'co_agent_id': self.agent_id.id
                }
                self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                # jika book_obj provider ada rodextrip kirim
                resv_obj = self.env[self.res_model].search([('name', '=', self.referenced_document)])
                for rec in resv_obj.provider_booking_ids:
                    if 'rodextrip' in rec.provider_id.code:
                        # tembak gateway
                        data = {
                            # 'referenced_document_external': 'AL.20120301695',
                            'referenced_document_external': rec.pnr2,
                            'res_model': self.res_model,
                            'provider': rec.provider_id.code,
                            'type': 'confirm'
                        }
                        self.env['tt.refund.api.con'].send_refund_request(data, self.agent_id.ho_id.id)
            else:
                _logger.info('Refund Confirmed email for {} is already created!'.format(self.name))
                raise Exception('Refund Confirmed email for {} is already created!'.format(self.name))
        except Exception as e:
            _logger.info('Error Create Email Queue')

    def confirm_refund_from_button_ho(self):
        if not ({self.env.ref('tt_base.group_after_sales_master_level_3').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 7')
        if self.state != 'draft':
            raise UserError("Cannot Confirm because state is not 'draft'.")

        estimate_refund_date = date.today() + relativedelta(days=self.refund_type_id.days)

        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
            'refund_date_ho': estimate_refund_date,
        })
        for rec in self.refund_line_ids:
            rec.set_to_confirm()

        try:
            mail_created = self.env['tt.email.queue'].sudo().search(
                [('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'refund_confirmed')],
                limit=1)
            if not mail_created:
                temp_data = {
                    'provider_type': 'refund',
                    'order_number': self.name,
                    'type': 'confirmed',
                }
                temp_context = {
                    'co_agent_id': self.agent_id.id
                }
                self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                # jika book_obj provider ada rodextrip kirim
                resv_obj = self.env[self.res_model].search([('name', '=', self.referenced_document)])
                for rec in resv_obj.provider_booking_ids:
                    if 'rodextrip' in rec.provider_id.code:
                        # tembak gateway
                        data = {
                            # 'referenced_document_external': 'AL.20120301695',
                            'referenced_document_external': rec.pnr2,
                            'res_model': self.res_model,
                            'provider': rec.provider_id.code,
                            'type': 'confirm'
                        }
                        self.env['tt.refund.api.con'].send_refund_request(data, self.agent_id.ho_id.id)
            else:
                _logger.info('Refund Confirmed email for {} is already created!'.format(self.name))
                raise Exception('Refund Confirmed email for {} is already created!'.format(self.name))
        except Exception as e:
            _logger.info('Error Create Email Queue')

    def refund_request_sent_to_agent_api(self, data, ctx):
        try:
            _logger.info('get webhook refund api confirm')
            _logger.info(json.dumps(data))
            data = data['data']
            refund_obj = self.search([('referenced_document_external', '=', data['reference_document']), ('state','=','confirm')], limit=1)
            if refund_obj:
                for rec in refund_obj:
                    for idx, refund_data in enumerate(rec.refund_line_ids):
                        if refund_data.total_vendor != 0:
                            refund_data.commission_fee += data['refund_list'][idx]['commission_fee']
                            refund_data.charge_fee += data['refund_list'][idx]['charge_fee']
                refund_obj.send_refund_from_button([[]])
                _logger.info('webhook done send back to HO')
                res = ERR.get_no_error()
            else:
                res = ERR.get_error(500)
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(500, additional_message='refund not found')
        return res

    def send_refund_from_button_backend(self):
        if not ({self.env.ref('tt_base.group_after_sales_master_level_3').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 8')
        self.send_refund_from_button()

    def send_webhook_refund(self, data, action, child_id):
        vals = {
            'provider_type': 'offline', ## seharusnya untuk airline tetapi di btbo2 bikin offline
            'action': action,
            'data': data,
            'child_id': child_id
        }
        _logger.info('webhook start')
        self.env['tt.api.webhook.data'].notify_subscriber(vals)
        _logger.info('webhook done')

    def send_refund_from_button(self, list=[]):
        if self.state != 'confirm':
            raise UserError("Cannot Send because state is not 'confirm'.")

        # klik dari HO tetapi untuk bookingan BTBO2
        resv_obj = self.env[self.res_model].search([('name', '=', self.referenced_document)])
        if resv_obj.agent_type_id == self.env.ref('tt_base.agent_type_btbo2'):
            _logger.info('btbo2 send refund api')
            for credential in resv_obj.user_id.credential_ids.webhook_rel_ids:
                if "webhook/content" in credential.url:
                    _logger.info('send webhook to child refund')
                    ## check lebih efisien check api ccredential usernya punya webhook visa, atau kalau api user selalu di notify
                    ## tetapi nanti filterny sendiri ke kirm ato enda
                    refund_list = []
                    for rec in self.refund_line_ids:
                        refund_list.append({
                            'name': rec.name,
                            'commission_fee': rec.commission_fee,
                            'charge_fee': rec.charge_fee
                        })
                    data = {
                        'refund_type': self.refund_type_id.name,
                        'type': 'send_to_agent_api',
                        'refund_list': refund_list,
                        'reference_document': self.referenced_document,
                        # 'referenced_document': 'AL.20120301695',
                    }

                    self.send_webhook_refund(data, 'refund_request_sent_to_agent_api', resv_obj.user_id.id)
                    break
        total_vendor = 100
        if len(list) == 0:
            total_vendor = 0
            for rec in self.refund_line_ids:
                rec.total_vendor = 0
        else:
            for rec in self.refund_line_ids:
                rec.total_vendor = rec.total_vendor - len(list)
                if total_vendor == 100:
                    total_vendor = rec.total_vendor
        if total_vendor == 0:
            total_vendor_reset = len(resv_obj.provider_booking_ids)
            for rec in self.refund_line_ids:
                rec.total_vendor = total_vendor_reset
            self.write({
                'state': 'sent',
                'sent_uid': self.env.user.id,
                'sent_date': datetime.now(),
                'hold_date': datetime.now() + relativedelta(days=3),
            })
            for rec in self.refund_line_ids:
                rec.set_to_sent()

    def validate_refund_api(self, data, ctx):
        try:
            _logger.info('get webhook refund api confirm')
            _logger.info(json.dumps(data))
            data = data['data']
            refund_obj = self.search([('referenced_document_external', '=', data['reference_document']), ('state','=','sent')], limit=1)
            total_refund = 100
            if refund_obj:
                for rec in refund_obj:
                    for idx, refund_data in enumerate(rec.refund_line_ids):
                        if refund_data.total_vendor != 0:
                            refund_data.total_vendor -= 1
                            total_refund = refund_data.total_vendor
                if total_refund == 0:
                    refund_obj.validate_refund_from_button()
                _logger.info('webhook done send back to HO')
                res = ERR.get_no_error()
            else:
                res = ERR.get_error(500)
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(500, additional_message='refund not found')
        return res

    def validate_refund_from_button_api(self, data, ctx):
        try:
            _logger.info(json.dumps(data))
            refund_obj = self.search([('referenced_document', '=', data['referenced_document_external']),('state','=','sent')], limit=1)
            if refund_obj:
                refund_obj.validate_refund_from_button()
                res = ERR.get_no_error()
            else:
                res = ERR.get_error(500)
            _logger.info(json.dumps(res))
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(500, additional_message='refund not found')
        return res

    def validate_refund_from_button(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('tt_base.group_tt_corpor_user').id, self.env.ref('tt_base.group_after_sales_master_level_3').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 9')
        if self.state != 'sent':
            raise UserError("Cannot Validate because state is not 'Sent'.")

        # agent to HO
        resv_obj = self.env[self.res_model].search([('name', '=', self.referenced_document)])
        total_vendor = 0
        for rec in resv_obj.provider_booking_ids:
            total_vendor += 1
            if 'rodextrip' in rec.provider_id.code:
                # tembak gateway
                data = {
                    # 'referenced_document_external': 'AL.20120301695',
                    'referenced_document_external': rec.pnr2,
                    'res_model': self.res_model,
                    'provider': rec.provider_id.code,
                    'type': 'validate'
                }
                self.env['tt.refund.api.con'].send_refund_request(data, self.agent_id.ho_id.id)

        # HO ke BTBO2
        if resv_obj.agent_type_id == self.env.ref('tt_base.agent_type_btbo2'):
            _logger.info('btbo2 send refund api')
            for credential in resv_obj.user_id.credential_ids.webhook_rel_ids:
                if "webhook/content" in credential.url:
                    _logger.info('send webhook to child refund')
                    ## check lebih efisien check api ccredential usernya punya webhook visa, atau kalau api user selalu di notify
                    ## tetapi nanti filterny sendiri ke kirm ato enda
                    refund_list = []
                    for rec in self.refund_line_ids:
                        refund_list.append({
                            'name': rec.name,
                            'extra_charge_amount': rec.extra_charge_amount,
                            'real_refund_amount': rec.real_refund_amount
                        })
                    data = {
                        'refund_type': self.refund_type_id.name,
                        'type': 'validate_from_button_api',
                        'refund_list': refund_list,
                        'reference_document': self.referenced_document,
                        # 'reference_document': 'TN.21010627702',
                    }

                    self.send_webhook_refund(data, 'finalize_refund_from_button_api', resv_obj.user_id.id)
                    break

        for rec in self.refund_line_ids:
            rec.total_vendor = total_vendor

        self.write({
            'state': 'validate',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now(),
            'final_admin_fee': self.admin_fee_ho + self.admin_fee_agent,
            'final_admin_fee_ho': self.admin_fee_ho,
            'final_admin_fee_agent': self.admin_fee_agent,
            'hold_date': False
        })

        # jika rodextrip send webhook ke BTBO jika btbo check book_obj provider ada rodextrip kirim

    def finalize_refund_from_button_api(self, data, ctx):
        try:
            _logger.info('get webhook refund api finalization')
            data = data['data']
            total_vendor = 100
            refund_obj = self.search([('referenced_document_external', '=', data['reference_document']), ('state','=','validate')], limit=1)
            if refund_obj:
                for rec in refund_obj:
                    for idx, refund_data in enumerate(rec.refund_line_ids):
                        if refund_data.total_vendor != 0:
                            refund_data.extra_charge_amount += data['refund_list'][idx]['extra_charge_amount']
                            refund_data.real_refund_amount += data['refund_list'][idx]['real_refund_amount']
                refund_obj.finalize_refund_from_button([[]])
                _logger.info('webhook done send back to HO')
                res = ERR.get_no_error()
            else:
                res = ERR.get_error(500)
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(500, additional_message='refund not found')
        return res

    def finalize_refund_from_button_backend(self):
        if not ({self.env.ref('tt_base.group_after_sales_master_level_3').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 10')
        self.finalize_refund_from_button()

    def finalize_refund_from_button(self, list=[]):
        if self.state != 'validate':
            raise UserError("Cannot finalize because state is not 'Validated'.")

        # klik dari HO tetapi untuk bookingan BTBO2
        total_vendor_reset = 0
        resv_obj = self.env[self.res_model].search([('name', '=', self.referenced_document)])
        for rec in resv_obj.provider_booking_ids:
            total_vendor_reset += 1
        if resv_obj.agent_type_id == self.env.ref('tt_base.agent_type_btbo2'):
            _logger.info('btbo2 send refund api')
            for credential in resv_obj.user_id.credential_ids.webhook_rel_ids:
                if "webhook/content" in credential.url:
                    _logger.info('send webhook to child refund')
                    ## check lebih efisien check api ccredential usernya punya webhook visa, atau kalau api user selalu di notify
                    ## tetapi nanti filterny sendiri ke kirm ato enda
                    refund_list = []
                    for rec in self.refund_line_ids:
                        refund_list.append({
                            'name': rec.name,
                            'extra_charge_amount': rec.extra_charge_amount,
                            'real_refund_amount': rec.real_refund_amount
                        })
                    data = {
                        'refund_type': self.refund_type_id.name,
                        'type': 'finalize_refund_from_button_api',
                        'refund_list': refund_list,
                        'reference_document': self.referenced_document,
                        # 'reference_document': 'TN.21010627702',
                    }

                    self.send_webhook_refund(data, 'finalize_refund_from_button_api', resv_obj.user_id.id)
                    break

        total_vendor = 100
        if len(list) == 0:
            total_vendor = 0
            for rec in self.refund_line_ids:
                rec.total_vendor = 0
        else:
            for rec in self.refund_line_ids:
                rec.total_vendor = rec.total_vendor - len(list)
                if total_vendor == 100:
                    total_vendor = rec.total_vendor
        if total_vendor == 0:
            for rec in self.refund_line_ids:
                rec.total_vendor = total_vendor_reset
            book_obj = self.env[self.res_model].browse(int(self.res_id))
            provider_len = len(book_obj.provider_booking_ids.ids)
            for idx, rec in enumerate(book_obj.provider_booking_ids):
                if idx == provider_len - 1:
                    rec.action_refund(True)
                else:
                    rec.action_refund()

            self.write({
                'state': 'final',
                'final_uid': self.env.user.id,
                'final_date': datetime.now()
            })

            for rec in self.refund_line_ids:
                rec.set_to_finalize()

            try:
                mail_created = self.env['tt.email.queue'].sudo().search(
                    [('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'refund_finalized')],
                    limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'refund',
                        'order_number': self.name,
                        'type': 'finalized',
                    }
                    temp_context = {
                        'co_agent_id': self.agent_id.id
                    }
                    self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                else:
                    _logger.info('Refund Finalized email for {} is already created!'.format(self.name))
                    raise Exception('Refund Finalized email for {} is already created!'.format(self.name))
            except Exception as e:
                _logger.info('Error Create Email Queue')

    def action_approve_api(self, data, ctx):
        try:
            _logger.info('get webhook refund api approve')
            _logger.info(json.dumps(data))
            data = data['data']
            refund_obj = self.search([('referenced_document_external', '=', data['reference_document']), ('state','=','final')], limit=1)
            if refund_obj:
                refund_obj.is_vendor_received = True
                refund_obj.action_approve([[]])
                _logger.info('webhook done send back to HO')
                res = ERR.get_no_error()
            else:
                res = ERR.get_error(500)
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(500, additional_message='refund not found')
        return res

    def action_approve_backend(self):
        if not ({self.env.ref('tt_base.group_after_sales_master_level_5').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 11')
        self.action_approve()

    def action_approve(self, list=[]):
        if self.state != 'final':
            raise UserError("Cannot approve because state is not 'Final'.")
        if not self.is_vendor_received:
            raise UserError("Please wait until you received the refund payment from vendor!")

        resv_obj = self.env[self.res_model].search([('name', '=', self.referenced_document)], limit=1)
        if not resv_obj.check_approve_refund_eligibility():
            raise UserError("Refund for this reservation can only be approved after all related invoices have been paid.")
        if resv_obj.agent_type_id == self.env.ref('tt_base.agent_type_btbo2'):
            _logger.info('btbo2 send refund api')
            for credential in resv_obj.user_id.credential_ids.webhook_rel_ids:
                if "webhook/content" in credential.url:
                    _logger.info('send webhook to child refund')
                    ## check lebih efisien check api ccredential usernya punya webhook visa, atau kalau api user selalu di notify
                    ## tetapi nanti filterny sendiri ke kirm ato enda
                    data = {
                        'refund_type': self.refund_type_id.name,
                        'type': 'action_approve_api',
                        'reference_document': self.referenced_document,
                        # 'reference_document': 'TN.21010627702',
                    }

                    self.send_webhook_refund(data, 'action_approve_api', resv_obj.user_id.id)
                    break

        total_vendor = 100
        if len(list) == 0:
            total_vendor = 0
            for rec in self.refund_line_ids:
                rec.total_vendor = 0
        else:
            for rec in self.refund_line_ids:
                rec.total_vendor = rec.total_vendor - len(list)
                if total_vendor == 100:
                    total_vendor = rec.total_vendor

        if total_vendor == 0:
            credit = 0
            debit = self.refund_amount
            if debit < 0:
                credit = debit * -1
                debit = 0

            ledger_type = 4
            self.env['tt.ledger'].create_ledger_vanilla(
                self.res_model,
                self.res_id,
                'Refund : %s' % (self.name),
                self.name,
                datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                self.agent_id.id,
                False,
                debit,
                credit,
                'Refund for %s (Ref PNR: %s)' % (self.referenced_document, self.referenced_pnr),
                **{'refund_id': self.id}
            )

            if self.final_admin_fee_ho:
                debit = 0
                credit = self.final_admin_fee_ho
                ledger_type = 6
                self.env['tt.ledger'].create_ledger_vanilla(
                    self.res_model,
                    self.res_id,
                    'Refund Admin Fee: %s' % (self.name),
                    self.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    ledger_type,
                    self.currency_id.id,
                    self.env.user.id,
                    self.agent_id.id,
                    False,
                    debit,
                    credit,
                    'Refund Admin Fee for %s (Ref PNR: %s)' % (self.referenced_document, self.referenced_pnr),
                    **{'refund_id': self.id}
                )

                ho_agent = self.agent_id.ho_id
                credit = 0
                debit = self.final_admin_fee_ho
                self.env['tt.ledger'].create_ledger_vanilla(
                    self.res_model,
                    self.res_id,
                    'Refund Admin Fee: %s' % (self.name),
                    self.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    ledger_type,
                    self.currency_id.id,
                    self.env.user.id,
                    ho_agent and ho_agent.id or False,
                    False,
                    debit,
                    credit,
                    'Refund Admin Fee for %s (Ref PNR: %s)' % (self.referenced_document, self.referenced_pnr),
                    **{'refund_id': self.id}
                )

            if self.final_admin_fee_agent:
                debit = 0
                credit = self.final_admin_fee_agent
                ledger_type = 4
                self.env['tt.ledger'].create_ledger_vanilla(
                    self.res_model,
                    self.res_id,
                    'Refund Agent Admin Fee: %s' % (self.name),
                    self.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    ledger_type,
                    self.currency_id.id,
                    self.env.user.id,
                    self.agent_id.id,
                    False,
                    debit,
                    credit,
                    'Refund Agent Admin Fee for %s (Ref PNR: %s)' % (self.referenced_document, self.referenced_pnr),
                    **{'refund_id': self.id}
                )

                credit = 0
                debit = self.final_admin_fee_agent
                ledger_type = 3
                self.env['tt.ledger'].create_ledger_vanilla(
                    self.res_model,
                    self.res_id,
                    'Refund Agent Admin Fee: %s' % (self.name),
                    self.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    ledger_type,
                    self.currency_id.id,
                    self.env.user.id,
                    self.agent_id.id,
                    False,
                    debit,
                    credit,
                    'Refund Agent Admin Fee for %s (Ref PNR: %s)' % (self.referenced_document, self.referenced_pnr),
                    **{'refund_id': self.id}
                )

            self.write({
                'state': 'approve',
                'approve_uid': self.env.user.id,
                'approve_date': datetime.now()
            })

            for rec in self.refund_line_ids:
                rec.set_to_done()

    def create_profit_loss_ledger(self):
        if not ({self.env.ref('tt_base.group_after_sales_master_level_3').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 12')
        value = self.real_refund_amount - self.refund_amount
        if self.real_refund_amount != 0 and value != 0 and not self.profit_loss_created:
            debit = value >= 0 and value or 0
            credit = value < 0 and value * -1 or 0

            ledger_type = 4
            ho_agent = self.agent_id.ho_id

            self.env['tt.ledger'].create_ledger_vanilla(
                self.res_model,
                self.res_id,
                'Profit&Loss : %s' % (self.name),
                self.name,
                datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                ho_agent and ho_agent.id or False,
                False,
                debit,
                credit,
                'Profit&Loss for %s Refund (Ref PNR: %s)' % (self.referenced_document, self.referenced_pnr),
                **{'refund_id': self.id}
            )
            self.sudo().write({
                'profit_loss_created': True
            })
        else:
            raise UserError(_('Profit & Loss Ledger has already been created, or HO has no Profit/Loss.'))

    def set_to_approve(self):
        if not ({self.env.ref('tt_base.group_after_sales_level_4').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 13')
        for rec in self.refund_line_cust_ids:
            rec.sudo().unlink()
        self.write({
            'state': 'approve',
        })

    def refund_cor_payment(self):
        pass

    def action_payment(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('tt_base.group_after_sales_master_level_4').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 14')
        if self.state != 'approve':
            raise UserError("Cannot process payment to customer because state is not 'approved'.")

        fee = len(self.refund_line_ids) > 0 and self.final_admin_fee / len(self.refund_line_ids) or 0
        for rec in self.refund_line_cust_ids:
            rec.sudo().unlink()
        for rec in self.refund_line_ids:
            self.env['tt.refund.line.customer'].create({
                'refund_id': self.id,
                'name': rec.name,
                'birth_date': rec.birth_date,
                'refund_amount': rec.refund_amount - fee,
            })
        self.write({
            'state': 'payment',
            'payment_uid': self.env.user.id,
            'payment_date': datetime.now()
        })

    def action_approve_cust(self):
        if not ({self.env.ref('base.group_erp_manager').id, self.env.ref('tt_base.group_after_sales_master_level_5').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 15')
        if self.state != 'payment':
            raise UserError("Cannot process payment to customer because state is not 'approved'.")
        self.write({
            'state': 'approve_cust',
            'approve2_uid': self.env.user.id,
            'approve2_date': datetime.now()
        })

    def action_done(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('tt_base.group_after_sales_master_level_3').id, self.env.ref('tt_base.group_tt_corpor_user').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 16')
        state_list = ['approve_cust']
        if self.customer_parent_id.customer_parent_type_id.id == self.env.ref('tt_base.customer_type_fpo').id:
            state_list.append('approve')
        if self.state not in state_list:
            raise UserError("Cannot set the transaction to Done because state is not 'approved'. Payment to Customer needs to be processed if the customer is COR/POR.")

        tot_citra_fee = 0
        for rec in self.refund_line_cust_ids:
            tot_citra_fee += rec.citra_fee

        if tot_citra_fee:
            credit = tot_citra_fee
            debit = 0
            ledger_type = 4
            self.env['tt.ledger'].sudo().create_ledger_vanilla(
                self.res_model,
                self.res_id,
                'Refund Agent Additional Fee : %s' % (self.name),
                self.name,
                datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                self.agent_id.id,
                False,
                debit,
                credit,
                'Refund Agent Additional Fee for %s (Ref PNR: %s)' % (self.referenced_document, self.referenced_pnr),
                **{'refund_id': self.id}
            )

            credit = 0
            debit = tot_citra_fee
            ledger_type = 3
            self.env['tt.ledger'].sudo().create_ledger_vanilla(
                self.res_model,
                self.res_id,
                'Refund Agent Additional Fee : %s' % (self.name),
                self.name,
                datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                self.agent_id.id,
                False,
                debit,
                credit,
                'Refund Agent Additional Fee for %s (Ref PNR: %s)' % (self.referenced_document, self.referenced_pnr),
                **{'refund_id': self.id}
            )

            if self.customer_parent_id.customer_parent_type_id.id != self.env.ref('tt_base.customer_type_fpo').id:
                self.refund_cor_payment()

        self.write({
            'state': 'done',
            'done_uid': self.env.user.id,
            'done_date': datetime.now()
        })

        try:
            mail_created = self.env['tt.email.queue'].sudo().search(
                [('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'refund_done')],
                limit=1)
            if not mail_created:
                temp_data = {
                    'provider_type': 'refund',
                    'order_number': self.name,
                    'type': 'done',
                }
                temp_context = {
                    'co_agent_id': self.agent_id.id
                }
                self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
            else:
                _logger.info('Refund Done email for {} is already created!'.format(self.name))
                raise Exception('Refund Done email for {} is already created!'.format(self.name))
        except Exception as e:
            _logger.info('Error Create Email Queue')

    def cancel_refund_from_button(self):
        if self.state in ['validate', 'final']:
            if not self.cancel_message:
                raise UserError("Please fill the cancellation message!")
        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })

    def cancel_refund_reverse_ledger(self):
        if not self.env.user.has_group('tt_base.group_after_sales_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 17')
        for rec in self.ledger_ids:
            if not rec.is_reversed:
                rec.reverse_ledger()

        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })

    def open_reference(self):
        try:
            form_id = self.env[self.res_model].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def toggle_is_vendor_received(self):
        if not ({self.env.ref('tt_base.group_after_sales_master_level_5').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 18')
        self.is_vendor_received = not self.is_vendor_received

    def print_refund_to_agent(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
            'is_ho': True
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        refund_ho_printout_action = self.env.ref('tt_report_common.action_report_printout_refund_ho')
        if not self.printout_refund_ho_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            # if self.user_id:
            #     co_uid = self.user_id.id
            # else:
            co_uid = self.env.user.id

            pdf_report = refund_ho_printout_action.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = refund_ho_printout_action.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Refund HO %s.pdf' % self.name,
                    'file_reference': 'Refund HO Printout',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_refund_ho_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_refund_ho_id.url,
        }
        return url
        # return refund_ho_printout_id.report_action(self, data=datas)

    def print_refund_to_agent_cust(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
            'is_agent': True
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        refund_ho_cust_printout_action = self.env.ref('tt_report_common.action_report_printout_refund_ho_cust')
        if not self.printout_refund_ho_cust_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            # if self.user_id:
            #     co_uid = self.user_id.id
            # else:
            co_uid = self.env.user.id

            pdf_report = refund_ho_cust_printout_action.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = refund_ho_cust_printout_action.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Refund %s.pdf' % self.name,
                    'file_reference': 'Refund HO Cust Printout',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_refund_ho_cust_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_refund_ho_cust_id.url,
        }
        return url
        # return refund_ho_printout_id.report_action(self, data=datas)

    def print_refund_to_cust(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        refund_printout_action = self.env.ref('tt_report_common.action_report_printout_refund')
        if not self.printout_refund_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            # if self.user_id:
            #     co_uid = self.user_id.id
            # else:
            co_uid = self.env.user.id

            pdf_report = refund_printout_action.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = refund_printout_action.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Refund %s.pdf' % self.name,
                    'file_reference': 'Refund Printout',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_refund_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_refund_id.url,
        }
        return url
        # return refund_printout_id.report_action(self, data=datas)

    def print_refund_to_cust_est(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
            'is_est': True
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        refund_printout_est_action = self.env.ref('tt_report_common.action_report_printout_refund')
        if not self.printout_refund_est_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            # if self.user_id:
            #     co_uid = self.user_id.id
            # else:
            co_uid = self.env.user.id

            pdf_report = refund_printout_est_action.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = refund_printout_est_action.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Refund Est %s.pdf' % self.name,
                    'file_reference': 'Refund Estimated Printout',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_refund_est_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_refund_est_id.url,
        }
        return url
        # return refund_printout_id.report_action(self, data=datas)

    def get_refund_data(self):
        resv_obj = self.env[self.res_model].browse(self.res_id)

        refund_lines = []
        for line in self.refund_line_ids:
            line_values = line.to_dict()
            refund_lines.append(line_values)

        refund_line_customers = []
        for cust in self.refund_line_cust_ids:
            cust_values = cust.to_dict()
            refund_line_customers.append(cust_values)

        new_vals = {
            'refund_number': self.name,
            'agent': self.agent_id.name,
            'agent_type': self.agent_type_id.name,
            'customer_parent': self.customer_parent_id.name,
            'customer_parent_type': self.customer_parent_type_id.name,
            'booker': self.booker_id.name,
            'currency': self.currency_id.name,
            'service_type': self.service_type,
            'direction': resv_obj.direction,
            'sector_type': resv_obj.sector_type,
            'resv_order_number': self.referenced_document,
            'pnr': self.referenced_pnr,

            'refund_date': self.refund_date and self.refund_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'refund_date_ho': self.refund_date_ho and self.refund_date_ho.strftime('%Y-%m-%d %H:%M:%S') or '',
            'real_refund_date': self.real_refund_date and self.real_refund_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'cust_refund_date': self.cust_refund_date and self.cust_refund_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'refund_type': self.refund_type_id.name,

            'refund_amount': self.refund_amount,
            'admin_fee': self.admin_fee,
            'admin_fee_ho': self.admin_fee_ho,
            'admin_fee_agent': self.admin_fee_agent,
            'total_amount': self.total_amount,
            'total_amount_cust': self.total_amount_cust,
            'final_admin_fee': self.final_admin_fee,
            'final_admin_fee_ho': self.final_admin_fee_ho,
            'final_admin_fee_agent': self.final_admin_fee_agent,
            'booking_description': self.booking_desc and self.booking_desc or '',
            'notes': self.notes and self.notes or '',
            'refund_lines': refund_lines,
            'refund_line_customers': refund_line_customers,
            'created_by_api': self.created_by_api,
            'state': self.state,
        }

        return new_vals

    # temporary function
    def convert_refund_type(self):
        all_refunds = self.env['tt.refund'].sudo().search([])
        for rec in all_refunds:
            if rec.refund_type == 'quick':
                rec.refund_type_id = self.env.ref('tt_accounting.refund_type_quick_refund').id
            elif rec.refund_type == 'regular':
                rec.refund_type_id = self.env.ref('tt_accounting.refund_type_regular_refund').id
            else:
                rec.refund_type_id = False
