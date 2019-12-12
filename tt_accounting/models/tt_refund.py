from odoo import api,models,fields
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
from ...tools import variables


class TtProviderRefund(models.Model):
    _name = "tt.provider.refund"
    _description = "Provider Refund Model"

    name = fields.Char('PNR', readonly=True)
    refund_id = fields.Many2one('tt.refund', 'Refund', ondelete='cascade')
    res_model = fields.Char(
        'Related Provider Name', index=True, readonly=True)
    res_id = fields.Integer(
        'Related Provider ID', index=True, readonly=True, help='Id of the followed resource')


class TtRefund(models.Model):
    _name = "tt.refund"
    _inherit = 'tt.history'
    _description = "Refund Model"
    _order = 'id DESC'

    name = fields.Char('Name', readonly=True, default='New', copy=False)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('sent', 'Sent'), ('validate', 'Validated'), ('approve', 'Approved'),
                              ('done', 'Done'), ('cancel', 'Canceled'), ('expired', 'Expired')], 'Status', default='draft',
                             help=" * The 'Draft' status is used for Agent to make refund request.\n"
                                  " * The 'Confirmed' status is used for HO to confirm and process the request.\n"
                                  " * The 'Sent' status is used for HO to send the request back to Agent with a set refund amount.\n"
                                  " * The 'Validated' status is used for Agent to final check and validate the request.\n"
                                  " * The 'Approved' status is used for HO to approve and process the request.\n"
                                  " * The 'Done' status means the agent's balance has been refunded.\n"
                                  " * The 'Canceled' status is used for Agent or HO to cancel the request.\n"
                                  " * The 'Expired' status means the request has been expired.\n")
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True,
                               default=lambda self: self.env.user.agent_id, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                              readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    refund_date = fields.Date('Estimated Refund Date', default=date.today(), required=True, readonly=True, related='refund_date_ho')
    refund_date_ho = fields.Date('Estimated Refund Date', default=date.today(), required=False, readonly=True, states={'confirm': [('readonly', False), ('required', True)]})
    estimate_ho_refund_date = fields.Date('Estimated Refund Date from Vendor', required=False, readonly=True, states={'confirm': [('readonly', False), ('required', True)]})
    real_refund_date = fields.Date('Real Refund Date from Vendor', default=date.today(), required=True, readonly=False, states={'done': [('readonly', True)], 'approve': [('readonly', True)], 'draft': [('readonly', True)]})

    service_type = fields.Selection(lambda self: self.get_service_type(), 'Service Type', required=True, readonly=True)

    refund_type = fields.Selection([('quick', 'Quick Refund'), ('regular', 'Regular Refund')], 'Refund Type', required=True, default='regular', readonly=True,
                                   states={'draft': [('readonly', False)]})
    apply_adm_fee = fields.Boolean('Apply Admin Fee', default=True, readonly=True, states={'confirm': [('readonly', False)]})
    admin_fee_type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], 'Admin Fee Type', default='amount', readonly=True, states={'confirm': [('readonly', False)]})
    admin_fee_num = fields.Integer('Set Admin Fee', default=0, readonly=True, states={'confirm': [('readonly', False)]})
    refund_amount = fields.Integer('Estimated Refund Amount', default=0, required=True, readonly=True, related='refund_amount_ho')
    estimate_ho_refund_amount = fields.Integer('Estimated Refund Amount from Vendor', default=0, required=True, readonly=True, states={'confirm': [('readonly', False)]})
    real_refund_amount = fields.Integer('Real Refund Amount from Vendor', default=0, required=True, readonly=False, states={'done': [('readonly', True)], 'approve': [('readonly', True)], 'draft': [('readonly', True)]})
    refund_amount_ho = fields.Integer('Estimated Refund Amount', default=0, required=True, readonly=True, states={'confirm': [('readonly', False)]})
    admin_fee = fields.Integer('Total Admin Fee', default=0, readonly=True, compute="_compute_admin_fee")
    total_amount = fields.Integer('Total Amount', default=0, readonly=True, compute="_compute_total_amount")
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.provider.refund', 'refund_id', 'Provider Booking', readonly=True, states={'draft': [('readonly', False)]})

    referenced_document = fields.Char('Ref. Document', readonly=True)

    res_model = fields.Char(
        'Related Reservation Name', index=True, readonly=True)

    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)

    ledger_ids = fields.One2many('tt.ledger','refund_id')

    hold_date = fields.Datetime('Hold Date', readonly=True)
    confirm_date = fields.Datetime('Confirm Date', readonly=True)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    sent_date = fields.Datetime('Sent Date', readonly=True)
    sent_uid = fields.Many2one('res.users', 'Sent by', readonly=True)
    validate_date = fields.Datetime('Validate Date', readonly=True)
    validate_uid = fields.Many2one('res.users', 'Validated by', readonly=True)
    approve_date = fields.Datetime('Approved Date', readonly=True)
    approve_uid = fields.Many2one('res.users', 'Approved by', readonly=True)
    done_date = fields.Datetime('Done Date', readonly=True)
    done_uid = fields.Many2one('res.users', 'Done by', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Canceled by', readonly=True)
    cancel_date = fields.Datetime('Cancel Date', readonly=True)
    cancel_message = fields.Text('Cancelation Message', required=False, readonly=True, states={'approve': [('readonly', False)], 'validate': [('readonly', False)]})

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.refund')
        if 'service_type' in vals_list:
            vals_list['service_type'] = self.parse_service_type(vals_list['service_type'])

        return super(TtRefund, self).create(vals_list)

    @api.depends('apply_adm_fee', 'admin_fee_type', 'admin_fee_num', 'refund_amount')
    @api.onchange('apply_adm_fee', 'admin_fee_type', 'admin_fee_num', 'refund_amount')
    def _compute_admin_fee(self):
        for rec in self:
            if rec.apply_adm_fee:
                if rec.admin_fee_type == 'amount':
                    rec.admin_fee = rec.admin_fee_num
                else:
                    rec.admin_fee = (rec.admin_fee_num / 100) * rec.refund_amount
            else:
                rec.admin_fee = 0

    @api.depends('admin_fee', 'refund_amount')
    @api.onchange('admin_fee', 'refund_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.refund_amount - rec.admin_fee

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

    def confirm_refund_from_button(self):
        if self.state != 'draft':
            raise UserError("Cannot Confirm because state is not 'draft'.")
        if not self.provider_booking_ids:
            raise UserError("There is no Provider to refund.")

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

    def send_refund_from_button(self):
        if self.state != 'confirm':
            raise UserError("Cannot Send because state is not 'confirm'.")

        estimate_refund_date = self.refund_date+relativedelta(days=3)
        self.write({
            'state': 'sent',
            'sent_uid': self.env.user.id,
            'sent_date': datetime.now(),
            'hold_date': datetime.now() + relativedelta(days=3),
            'refund_date_ho': estimate_refund_date,
            'estimate_ho_refund_date': estimate_refund_date,
        })

    def validate_refund_from_button(self):
        if self.state != 'sent':
            raise UserError("Cannot Validate because state is not 'Sent'.")

        self.write({
            'state': 'validate',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now(),
            'hold_date': False
        })

    def approve_refund_from_button(self):
        if self.state != 'validate':
            raise UserError("Cannot Approve because state is not 'Validated'.")

        self.write({
            'state': 'approve',
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now()
        })

        if date.today() >= self.refund_date:
            self.action_done()

    def action_done(self):
        credit = 0
        debit = self.refund_amount
        if self.apply_adm_fee:
            debit -= self.admin_fee

        ledger_type = 4

        self.env['tt.ledger'].create_ledger_vanilla(
            self.res_model,
            self.res_id,
            'Refund : for %s' % (self.name),
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

        for rec in self.provider_booking_ids:
            prov_obj = self.env[rec.res_model].browse(int(rec.res_id))
            prov_obj.action_refund()

        self.write({
            'state': 'done',
            'done_uid': self.env.user.id,
            'done_date': datetime.now()
        })

    def cancel_refund_from_button(self):
        if self.state in ['validate', 'approve']:
            if not self.cancel_message:
                raise UserError("Please fill the cancellation message!")
        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })

    def reset_provider_booking(self):
        resv_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        ref_id_list = []
        for rec in resv_obj.refund_ids:
            for rec2 in rec.provider_booking_ids:
                ref_id_list.append({
                    'res_model': str(rec2.res_model),
                    'res_id': int(rec2.res_id)
                })
        for rec in resv_obj.provider_booking_ids:
            check_exist = {
                'res_model': str(rec._name),
                'res_id': int(rec.id)
            }
            if rec.state == 'issued' and check_exist not in ref_id_list:
                self.env['tt.provider.refund'].sudo().create({
                    'name': rec.pnr,
                    'res_id': rec.id,
                    'res_model': rec._name,
                    'refund_id': self.id,
                })

