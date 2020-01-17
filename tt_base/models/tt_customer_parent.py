from odoo import fields,api,models
from ...tools import ERR
from odoo.exceptions import UserError

class TtCustomerParent(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer.parent'
    _rec_name = 'name'
    _description = 'Tour & Travel - Customer Parent'

    name = fields.Char('Name', required=True,default="PT.")
    logo_thumb = fields.Binary('Agent Logo Thumb', compute="_get_logo_image", store=True, attachment=True) #fixme later

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', required=True)
    parent_agent_id = fields.Many2one('tt.agent', 'Parent', required=True)  # , default=lambda self: self.env.user.agent_id

    balance = fields.Monetary(string="Balance")
    actual_balance = fields.Monetary(string="Actual Balance", readonly=True, compute="_compute_actual_balance")
    credit_limit = fields.Monetary(string="Credit Limit")
    unprocessed_amount = fields.Monetary(string="Unprocessed Amount", readonly=True, compute="_compute_unprocessed_amount")

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    email = fields.Char(string="Email", required=False, )
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string='Currency')
    address_ids = fields.One2many('address.detail', 'agent_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'agent_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'agent_id', 'Social Media')
    customer_ids = fields.Many2many('tt.customer', 'tt_customer_customer_parent_rel','customer_parent_id','customer_id','Customer')
    user_ids = fields.One2many('res.users', 'agent_id', 'User')
    payment_acquirer_ids = fields.Char(string="Payment Acquirer", required=False, )  # payment_acquirer
    agent_bank_detail_ids = fields.One2many('agent.bank.detail', 'agent_id', 'Agent Bank')  # agent_bank_detail
    tac = fields.Text('Terms and Conditions', readonly=True)
    tax_percentage = fields.Float('Tax (%)', default=0)
    active = fields.Boolean('Active', default='True')

    def _compute_unprocessed_amount(self):
        for rec in self:
            total_amt = 0
            invoice_objs = self.env['tt.agent.invoice'].sudo().search([('customer_parent_id', '=', rec.id), ('state', 'in', ['draft', 'confirm'])])
            for rec2 in invoice_objs:
                for rec3 in rec2.invoice_line_ids:
                    total_amt += rec3.total
            rec.unprocessed_amount = total_amt

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
        return self.actual_balance >= amount

    #ledger history
    #booking History