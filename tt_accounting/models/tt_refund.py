from odoo import api,models,fields
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
from ...tools import variables


class TtProviderRefund(models.Model):
    _name = "tt.provider.refund"
    _description = "Provider Refund Model"

    name = fields.Char('PNR', readonly=True)
    refund_id = fields.Many2one('tt.refund', 'Refund')
    res_model = fields.Char(
        'Related Provider Name', index=True, readonly=True)
    res_id = fields.Integer(
        'Related Provider ID', index=True, readonly=True, help='Id of the followed resource')

    @api.depends('res_model', 'res_id')
    @api.onchange('res_model', 'res_id')
    def _compute_name(self):
        if self.res_model and self.res_id:
            provider_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
            self.name = provider_obj and provider_obj.pnr or ''


class TtRefund(models.Model):
    _name = "tt.refund"
    _description = "Refund Model"
    _order = 'id DESC'

    name = fields.Char('Name', readonly=True, default='New', copy=False)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('sent', 'Sent'), ('validate', 'Validated'),
                              ('cancel', 'Canceled')], 'Status', default='draft',
                             help=" * The 'Draft' status is used for Agent to make refund request.\n"
                                  " * The 'Confirmed' status is used for HO to confirm and process the request.\n"
                                  " * The 'Sent' status is used for HO to send the request back to Agent with a set refund amount.\n"
                                  " * The 'Validated' status is used for Agent to final check and validate the request, then ledger is created.\n"
                                  " * The 'Canceled' status is used for Agent or HO to cancel the request.\n")
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True,
                               default=lambda self: self.env.user.agent_id, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                    readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    date = fields.Date('Date',default=date.today())

    service_type = fields.Selection(lambda self: self.get_service_type(), 'Service Type', required=True, readonly=True)

    refund_type = fields.Selection([('quick', 'Quick Refund'), ('regular', 'Regular Refund')], 'Refund Type', required=True, default='regular', readonly=True,
                                states={'draft': [('readonly', False)]})
    apply_adm_fee = fields.Boolean('Apply Admin Fee', default=True, readonly=True, states={'confirm': [('readonly', False)]})
    admin_fee_type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], 'Refund Admin Fee', default='amount', readonly=True, states={'confirm': [('readonly', False)]})
    admin_fee_num = fields.Integer('Set Admin Fee', default=0, readonly=True, states={'confirm': [('readonly', False)]})
    refund_amount = fields.Integer('Refund Amount', default=0, required=True, readonly=True, related='refund_amount_ho')
    refund_amount_ho = fields.Integer('Refund Amount', default=0, required=True, readonly=True, states={'confirm': [('readonly', False)]})
    admin_fee = fields.Integer('Refund Admin Fee', default=0, readonly=True, compute="_compute_admin_fee")
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.provider.refund', 'refund_id', 'Provider Booking')

    referenced_document = fields.Char('Ref. Document', readonly=True)

    res_model = fields.Char(
        'Related Reservation Name', index=True, readonly=True)

    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)

    ledger_ids = fields.One2many('tt.ledger','refund_id')

    confirm_date = fields.Datetime('Confirm Date', readonly=True)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    validate_date = fields.Datetime('Validate Date', readonly=True)
    validate_uid = fields.Many2one('res.users', 'Validated by', readonly=True)
    approve_date = fields.Datetime('Approve Date', readonly=True)
    approve_uid = fields.Many2one('res.users', 'Approved by', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Canceled by', readonly=True)
    cancel_date = fields.Datetime('Cancel Date', readonly=True)
    cancel_message = fields.Text('Cancelation Message', readonly=True, states={'validate': [('readonly', False)]})


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

    def parse_service_type(self,type):
        return self.env['tt.provider.type'].browse(int(type)).code
        
    def get_service_type(self):
        return [(rec,rec.capitalize()) for rec in self.env['tt.provider.type'].get_provider_type()]

    def confirm_refund_from_button(self):
        if self.state != 'draft':
            raise UserError("Cannot Approve because state is not 'draft'.")

        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now()
        })

    def send_refund_from_button(self):
        if self.state != 'confirm':
            raise UserError("Cannot Approve because state is not 'confirm'.")

        self.write({
            'state': 'sent',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now()
        })

    def validate_refund_from_button(self):
        if self.state != 'sent':
            raise UserError("Cannot Approve because state is not 'Sent'.")

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

        self.write({
            'state': 'validate',
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now()
        })

    def cancel_refund_from_button(self):
        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })

