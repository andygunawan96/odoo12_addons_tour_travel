from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SetCustomerParentCreditLimitWizard(models.TransientModel):
    _name = "set.customer.parent.credit.limit.wizard"
    _description = 'Set Customer Parent Credit Limit Wizard'

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', required=True, readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string='Currency', readonly=True)
    credit_limit = fields.Monetary(string="Credit Limit")

    def set_cor_credit_limit(self):
        if self.env.user.has_group('tt_base.group_tt_corpor_user'):
            if self.customer_parent_id.id == self.env.user.customer_parent_id.id:
                raise UserError('You are not allowed to set your own credit limit.')
            if not self.env.user.customer_parent_id.is_master_customer_parent or not self.customer_parent_id.master_customer_parent_id or self.customer_parent_id.master_customer_parent_id.id != self.env.user.customer_parent_id.id:
                raise UserError('You can only set credit limit for your child customer parents.')

        master_cor_obj = self.customer_parent_id.master_customer_parent_id
        if not master_cor_obj:
            raise UserError('This feature can only be used by master customer parent user to set child customer parent credit limit.')
        if master_cor_obj.is_use_credit_limit_sharing:
            raise UserError('This feature is disabled as the master customer parent has credit limit sharing activated.')

        tot_credit_limit = 0
        for rec in master_cor_obj.child_customer_parent_ids.filtered(lambda x: x.id != self.customer_parent_id.id):
            tot_credit_limit += rec.credit_limit
        if tot_credit_limit + self.credit_limit > master_cor_obj.max_child_credit_limit:
            raise UserError('Total child customer parents credit limit cannot exceed their master limitation.')

        self.customer_parent_id.sudo().write({
            'credit_limit': self.credit_limit
        })
