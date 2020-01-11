from odoo import api,models,fields,_
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
from ...tools import variables


class TtRefundLine(models.Model):
    _name = "tt.refund.line"
    _description = "Refund Line Model"

    name = fields.Char('Name', readonly=True)
    birth_date = fields.Date('Birth Date', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    pax_price = fields.Monetary('Passenger Price', default=0, readonly=True)
    charge_fee = fields.Monetary('Charge Fee', default=0, readonly=True, states={'confirm': [('readonly', False)]})
    refund_amount = fields.Monetary('Expected Refund Amount', default=0, required=True, readonly=True, compute='_compute_refund_amount')
    real_refund_amount = fields.Monetary('Real Refund Amount', default=0, readonly=False, states={'draft': [('readonly', True)]})
    refund_id = fields.Many2one('tt.refund', 'Refund', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done')], 'State', default='draft', related='')

    @api.depends('pax_price', 'charge_fee')
    @api.onchange('pax_price', 'charge_fee')
    def _compute_refund_amount(self):
        for rec in self:
            rec.refund_amount = rec.pax_price - rec.charge_fee

    def set_to_draft(self):
        self.write({
            'state': 'draft',
        })

    def set_to_confirm(self):
        self.write({
            'state': 'confirm',
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
    agent_id = fields.Many2one('tt.agent', 'Agent', related='refund_id.agent_id')
    acquirer_id = fields.Many2one('payment.acquirer', 'Payment Acquirer', domain="[('agent_id','=',agent_id)]")

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
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True,
                               default=lambda self: self.env.user.agent_id)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                              readonly=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    refund_date = fields.Date('Expected Refund Date', default=date.today(), required=True, readonly=True, related='refund_date_ho')
    refund_date_ho = fields.Date('Expected Refund Date', default=date.today(), required=False, readonly=True, states={'confirm': [('readonly', False), ('required', True)]})
    real_refund_date = fields.Date('Real Refund Date from Vendor', default=date.today(), required=True, readonly=False, states={'done': [('readonly', True)], 'approve': [('readonly', True)], 'draft': [('readonly', True)]})
    cust_refund_date = fields.Datetime('Expected Cust. Refund Date', readonly=False, states={'done': [('readonly', True)]})

    service_type = fields.Selection(lambda self: self.get_service_type(), 'Service Type', required=True, readonly=True)

    refund_type = fields.Selection([('quick', 'Quick Refund (Max. 3 days process)'), ('regular', 'Regular Refund (40 days process)')], 'Refund Type', required=True, default='regular', readonly=True,
                                   states={'draft': [('readonly', False)]})
    admin_fee_id = fields.Many2one('tt.master.admin.fee', 'Admin Fee Type', domain=[('after_sales_type', '=', 'refund')], compute="_compute_admin_fee_id")
    refund_amount = fields.Monetary('Expected Refund Amount', default=0, required=True, readonly=True, compute='_compute_refund_amount', related='')
    real_refund_amount = fields.Monetary('Real Refund Amount from Vendor', default=0, readonly=True, compute='_compute_real_refund_amount')
    admin_fee = fields.Monetary('Admin Fee Amount', default=0, readonly=True, compute="_compute_admin_fee")
    total_amount = fields.Monetary('Total Amount', default=0, readonly=True, compute="_compute_total_amount")
    total_amount_cust = fields.Monetary('Total Amount (Customer)', default=0, readonly=True, compute="_compute_total_amount_cust")
    final_admin_fee = fields.Monetary('Admin Fee Amount', default=0, readonly=True)
    booking_desc = fields.Text('Booking Description', readonly=True)
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    refund_line_ids = fields.One2many('tt.refund.line', 'refund_id', 'Refund Line(s)', readonly=False)
    refund_line_cust_ids = fields.One2many('tt.refund.line.customer', 'refund_id', 'Payment to Customer(s)', readonly=True, states={'payment': [('readonly', False)]})

    referenced_pnr = fields.Char('Ref. PNR', readonly=True)
    referenced_document = fields.Char('Ref. Document', readonly=True)

    res_model = fields.Char('Related Reservation Name', index=True, readonly=True)

    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    profit_loss_created = fields.Boolean('Profit & Loss Created', default=False, readonly=True)

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
    cancel_message = fields.Text('Cancelation Message', required=False, readonly=True, states={'approve': [('readonly', False)], 'validate': [('readonly', False)]})

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code(self._name)
        if 'service_type' in vals_list:
            vals_list['service_type'] = self.parse_service_type(vals_list['service_type'])

        return super(TtRefund, self).create(vals_list)

    @api.depends('refund_type')
    @api.onchange('refund_type')
    def _compute_admin_fee_id(self):
        for rec in self:
            if rec.refund_type == 'quick':
                rec.admin_fee_id = self.env.ref('tt_accounting.admin_fee_refund_quick').id
            else:
                rec.admin_fee_id = self.env.ref('tt_accounting.admin_fee_refund_regular').id

    @api.depends('refund_line_ids')
    @api.onchange('refund_line_ids')
    def _compute_refund_amount(self):
        for rec in self:
            temp_total = 0
            for rec2 in rec.refund_line_ids:
                temp_total += rec2.refund_amount
            rec.refund_amount = temp_total

    @api.depends('refund_line_ids')
    @api.onchange('refund_line_ids')
    def _compute_real_refund_amount(self):
        for rec in self:
            temp_total = 0
            for rec2 in rec.refund_line_ids:
                temp_total += rec2.real_refund_amount
            rec.real_refund_amount = temp_total

    @api.depends('admin_fee_id', 'refund_amount', 'res_model', 'res_id')
    @api.onchange('admin_fee_id', 'refund_amount', 'res_model', 'res_id')
    def _compute_admin_fee(self):
        for rec in self:
            if rec.admin_fee_id:
                if rec.admin_fee_id.type == 'amount':
                    pnr_amount = 0
                    book_obj = self.env[rec.res_model].browse(int(rec.res_id))
                    for rec2 in book_obj.provider_booking_ids:
                        pnr_amount += 1
                else:
                    pnr_amount = 1
                rec.admin_fee = rec.admin_fee_id.get_final_adm_fee(rec.refund_amount, pnr_amount)
            else:
                rec.admin_fee = 0

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

    def action_expired(self):
        self.write({
            'state': 'expired',
        })

    def set_to_confirm(self):
        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
            'hold_date': False
        })
        for rec in self.refund_line_ids:
            rec.set_to_confirm()

    def confirm_refund_from_button(self):
        if self.state != 'draft':
            raise UserError("Cannot Confirm because state is not 'draft'.")

        if self.refund_type == 'quick':
            estimate_refund_date = date.today() + relativedelta(days=3)
        else:
            estimate_refund_date = date.today() + relativedelta(days=40)

        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
            'refund_date_ho': estimate_refund_date,
            'estimate_ho_refund_date': estimate_refund_date,
        })
        for rec in self.refund_line_ids:
            rec.set_to_confirm()

    def send_refund_from_button(self):
        if self.state != 'confirm':
            raise UserError("Cannot Send because state is not 'confirm'.")

        self.write({
            'state': 'sent',
            'sent_uid': self.env.user.id,
            'sent_date': datetime.now(),
            'hold_date': datetime.now() + relativedelta(days=3),
        })
        for rec in self.refund_line_ids:
            rec.set_to_done()

    def validate_refund_from_button(self):
        if self.state != 'sent':
            raise UserError("Cannot Validate because state is not 'Sent'.")

        self.write({
            'state': 'validate',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now(),
            'final_admin_fee': self.admin_fee,
            'hold_date': False
        })

    def finalize_refund_from_button(self):
        if self.state != 'validate':
            raise UserError("Cannot finalize because state is not 'Validated'.")

        book_obj = self.env[self.res_model].browse(int(self.res_id))
        for rec in book_obj.provider_booking_ids:
            rec.action_refund()

        self.write({
            'state': 'final',
            'final_uid': self.env.user.id,
            'final_date': datetime.now()
        })

        if date.today() >= self.refund_date:
            self.action_approve()

    def action_approve(self):
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
            self.referenced_document,
            datetime.now() + relativedelta(hours=7),
            ledger_type,
            self.currency_id.id,
            self.env.user.id,
            self.agent_id.id,
            self.customer_parent_id.id,
            debit,
            credit,
            'Refund for %s' % (self.referenced_document),
            **{'refund_id': self.id}
        )

        ledger_type = 6
        if self.final_admin_fee:
            debit = 0
            credit = self.final_admin_fee
            self.env['tt.ledger'].create_ledger_vanilla(
                self.res_model,
                self.res_id,
                'Refund Admin Fee: %s' % (self.name),
                self.referenced_document,
                datetime.now() + relativedelta(hours=7),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                self.agent_id.id,
                self.customer_parent_id.id,
                debit,
                credit,
                'Refund Admin Fee for %s' % (self.referenced_document),
                **{'refund_id': self.id}
            )

            ho_agent = self.env['tt.agent'].sudo().search(
                [('agent_type_id.id', '=', self.env.ref('tt_base.agent_type_ho').id)], limit=1)
            credit = 0
            debit = self.final_admin_fee
            self.env['tt.ledger'].create_ledger_vanilla(
                self.res_model,
                self.res_id,
                'Refund Admin Fee: %s' % (self.name),
                self.referenced_document,
                datetime.now() + relativedelta(hours=7),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                ho_agent and ho_agent[0].id or False,
                False,
                debit,
                credit,
                'Refund Admin Fee for %s' % (self.referenced_document),
                **{'refund_id': self.id}
            )

        self.write({
            'state': 'approve',
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now()
        })

    def create_profit_loss_ledger(self):
        value = self.real_refund_amount - self.refund_amount
        if value != 0 and not self.profit_loss_created:
            debit = value >= 0 and value or 0
            credit = value < 0 and value * -1 or 0

            ledger_type = 4
            ho_agent = self.env['tt.agent'].sudo().search(
                [('agent_type_id.id', '=', self.env.ref('tt_base.agent_type_ho').id)], limit=1)

            self.env['tt.ledger'].create_ledger_vanilla(
                self.res_model,
                self.res_id,
                'Profit&Loss : %s' % (self.name),
                self.referenced_document,
                datetime.now() + relativedelta(hours=7),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                ho_agent and ho_agent[0].id or False,
                False,
                debit,
                credit,
                'Profit&Loss for %s Refund' % (self.referenced_document),
                **{'refund_id': self.id}
            )
            self.sudo().write({
                'profit_loss_created': True
            })
        else:
            raise UserError(_('Profit & Loss Ledger has already been created, or HO has no Profit/Loss.'))

    def set_to_approve(self):
        for rec in self.refund_line_cust_ids:
            rec.sudo().unlink()
        self.write({
            'state': 'approve',
        })

    def action_payment(self):
        if self.agent_type_id.id in [self.env.ref('tt_base.agent_type_citra').id, self.env.ref('tt_base.agent_type_japro').id]:
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
        else:
            self.write({
                'state': 'done',
                'done_uid': self.env.user.id,
                'done_date': datetime.now()
            })

    def action_approve_cust(self):
        self.write({
            'state': 'approve_cust',
            'approve2_uid': self.env.user.id,
            'approve2_date': datetime.now()
        })

    def action_done(self):
        tot_citra_fee = 0
        for rec in self.refund_line_cust_ids:
            tot_citra_fee += rec.citra_fee

        if tot_citra_fee:
            credit = tot_citra_fee
            debit = 0
            ledger_type = 4
            self.env['tt.ledger'].create_ledger_vanilla(
                self.res_model,
                self.res_id,
                'Refund Agent Admin Fee : %s' % (self.name),
                self.referenced_document,
                datetime.now() + relativedelta(hours=7),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                self.agent_id.id,
                self.customer_parent_id.id,
                debit,
                credit,
                'Refund Agent Admin Fee for %s' % (self.referenced_document),
                **{'refund_id': self.id}
            )

            credit = 0
            debit = tot_citra_fee
            ledger_type = 3
            self.env['tt.ledger'].create_ledger_vanilla(
                self.res_model,
                self.res_id,
                'Refund Agent Admin Fee : %s' % (self.name),
                self.referenced_document,
                datetime.now() + relativedelta(hours=7),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                self.agent_id.id,
                self.customer_parent_id.id,
                debit,
                credit,
                'Refund Agent Admin Fee for %s' % (self.referenced_document),
                **{'refund_id': self.id}
            )

        self.write({
            'state': 'done',
            'done_uid': self.env.user.id,
            'done_date': datetime.now()
        })

    def cancel_refund_from_button(self):
        if self.state in ['validate', 'final']:
            if not self.cancel_message:
                raise UserError("Please fill the cancellation message!")
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

    def print_refund_to_agent(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
            'is_ho': True
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        refund_ho_printout_id = self.env.ref('tt_report_common.action_report_printout_refund_ho')
        return refund_ho_printout_id.report_action(self, data=datas)

    def print_refund_to_cust(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        refund_printout_id = self.env.ref('tt_report_common.action_report_printout_refund')
        return refund_printout_id.report_action(self, data=datas)

    def print_refund_to_cust_est(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
            'is_est': True
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        refund_printout_id = self.env.ref('tt_report_common.action_report_printout_refund')
        return refund_printout_id.report_action(self, data=datas)

