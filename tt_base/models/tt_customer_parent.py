from odoo import fields,api,models
from ...tools import ERR
from odoo.exceptions import UserError
from datetime import datetime


class TtCustomerParent(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer.parent'
    _rec_name = 'name'
    _description = 'Tour & Travel - Customer Parent'

    name = fields.Char('Name', required=True, default="PT.")
    logo = fields.Binary('Customer Logo')

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', required=True)
    parent_agent_id = fields.Many2one('tt.agent', 'Parent', required=True)  # , default=lambda self: self.env.user.agent_id

    balance = fields.Monetary(string="Balance")
    actual_balance = fields.Monetary(string="Actual Balance", readonly=True, compute="_compute_actual_balance")
    credit_limit = fields.Monetary(string="Credit Limit")
    unprocessed_amount = fields.Monetary(string="Unprocessed Amount", readonly=True, compute="_compute_unprocessed_amount")

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    email = fields.Char(string="Email")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string='Currency')
    address_ids = fields.One2many('address.detail', 'customer_parent_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'customer_parent_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'customer_parent_id', 'Social Media')
    customer_ids = fields.Many2many('tt.customer', 'tt_customer_customer_parent_rel','customer_parent_id','customer_id','Customer')
    user_ids = fields.One2many('res.users', 'agent_id', 'User')
    payment_acquirer_ids = fields.Char(string="Payment Acquirer", required=False, )  # payment_acquirer
    agent_bank_detail_ids = fields.One2many('agent.bank.detail', 'agent_id', 'Agent Bank')  # agent_bank_detail
    tac = fields.Text('Terms and Conditions', readonly=True)
    tax_percentage = fields.Float('Tax (%)', default=0)
    tax_identity_number = fields.Char('NPWP')
    company_bank_data = fields.Char('Company Bank Data')
    active = fields.Boolean('Active', default='True')
    state = fields.Selection([('draft', 'Draft'),('confirm', 'Confirmed'),('request', 'Requested'),('validate', 'Validated'),('done', 'Done'),('reject', 'Rejected')], 'State', default='draft', readonly=True)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    confirm_date = fields.Datetime('Confirmed Date', readonly=True)
    request_uid = fields.Many2one('res.users', 'Requested by', readonly=True)
    request_date = fields.Datetime('Requested Date', readonly=True)
    validate_uid = fields.Many2one('res.users', 'Validated by', readonly=True)
    validate_date = fields.Datetime('Validated Date', readonly=True)
    done_uid = fields.Many2one('res.users', 'Approved by', readonly=True)
    done_date = fields.Datetime('Approved Date', readonly=True)
    reject_uid = fields.Many2one('res.users', 'Rejected by', readonly=True)
    reject_date = fields.Datetime('Rejected Date', readonly=True)

    def _compute_unprocessed_amount(self):
        for rec in self:
            total_amt = 0
            invoice_objs = self.env['tt.agent.invoice'].sudo().search([('customer_parent_id', '=', rec.id), ('state', 'in', ['draft', 'confirm'])])
            for rec2 in invoice_objs:
                for rec3 in rec2.invoice_line_ids:
                    total_amt += rec3.total_after_tax

            ## check invoice billed tetapi sudah di bayar
            invoice_bill_objs = self.env['tt.agent.invoice'].sudo().search(
                [('customer_parent_id', '=', rec.id), ('state', 'in', ['bill','bill2']), ('paid_amount','>',0)])
            paid_amount = 0
            for billed_invoice in invoice_bill_objs:
                paid_amount += billed_invoice.paid_amount
            rec.unprocessed_amount = total_amt-paid_amount

    def _compute_actual_balance(self):
        for rec in self:
            rec.actual_balance = rec.credit_limit + rec.balance - rec.unprocessed_amount

    @api.model
    def create(self,vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('cust.par')
        return super(TtCustomerParent, self).create(vals_list)

    @api.model
    def customer_parent_action_view_customer(self):
        action = self.env.ref('tt_base.tt_customer_parent_action_view').read()[0]
        action['context'] = {
            'form_view_ref': 'tt_base.tt_customer_parent_form_view_customer',
            'tree_view_ref': 'tt_base.tt_customer_parent_tree_view_customer',
            'default_parent_agent_id': self.env.user.agent_id.id
        }
        action['domain'] = [('parent_agent_id', '=', self.env.user.agent_id.id)]
        return action
        # return {
        #     'name': 'Customer Parent',
        #     'type': 'ir.actions.act_window',
        #     'view_type': 'form',
        #     'view_mode': 'tree,form',
        #     'res_model': 'tt.customer.parent',
        #     'views': [(self.env.ref('tt_base.tt_customer_parent_tree_view_customer').id, 'tree'),
        #               (self.env.ref('tt_base.tt_customer_parent_form_view_customer').id, 'form')],
        #     'context': {
        #         'default_parent_agent_id': self.env.user.agent_id.id
        #     },
        #     'domain': [('parent_agent_id', '=', self.env.user.agent_id.id)]
        # }

    def check_balance_limit_api(self, customer_parent_id, amount):
        partner_obj = self.env['tt.customer.parent']

        if type(customer_parent_id) == str:
            partner_obj = self.env['tt.customer.parent'].search([('seq_id', '=', customer_parent_id)], limit=1)
        elif type(customer_parent_id) == int:
            partner_obj = self.env['tt.customer.parent'].browse(customer_parent_id)

        if not partner_obj:
            return ERR.get_error(1008)
        if not partner_obj.check_balance_limit(amount):
            return ERR.get_error(1007)
        else:
            return ERR.get_no_error()

    def check_balance_limit(self, amount):
        if not self.ensure_one():
            raise UserError('Can only check 1 agent each time got ' + str(len(self._ids)) + ' Records instead')
        return self.actual_balance >= (amount + (amount * self.tax_percentage / 100))

    def action_confirm(self):
        if self.state != 'draft':
            raise UserError("Cannot Confirm because state is not 'draft'.")
        if not self.address_ids or not self.phone_ids:
            raise UserError("Please fill at least one ADDRESS data and one PHONE data!")
        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now()
        })

    def action_request(self):
        if self.state != 'confirm':
            raise UserError("Cannot Submit Request because state is not 'confirm'.")

        self.write({
            'state': 'request',
            'request_uid': self.env.user.id,
            'request_date': datetime.now()
        })

    def action_validate(self):
        if self.state != 'request':
            raise UserError("Cannot Validate because state is not 'request'.")

        self.write({
            'state': 'validate',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now()
        })

    def set_to_validate(self):
        self.write({
            'state': 'validate',
        })

    def action_done(self):
        if self.state != 'validate':
            raise UserError("Cannot Approve because state is not 'validate'.")

        self.write({
            'state': 'done',
            'done_uid': self.env.user.id,
            'done_date': datetime.now()
        })

    def action_reject(self):
        if self.state == 'done':
            raise UserError("Cannot reject already approved Customer Parent.")

        self.write({
            'state': 'reject',
            'reject_uid': self.env.user.id,
            'reject_date': datetime.now()
        })

    def set_to_done(self):
        self.write({
            'state': 'done',
        })

    def set_to_draft(self):
        if self.state != 'reject':
            raise UserError("Please reject this Customer Parent before setting it to draft!")

        self.write({
            'state': 'draft',
        })

    #ledger history
    #booking History
