from odoo import api, fields, models, _


class CreateCustomerParentWizard(models.TransientModel):
    _name = "create.customer.parent.wizard"
    _description = 'Create Customer Parent Wizard'

    name = fields.Char('Name', required=True, default="PT.")

    def get_customer_parent_domain(self):
        return [('id', '!=', self.env.ref('tt_base.customer_type_fpo').id)]

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', required=True, domain=get_customer_parent_domain)
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, readonly=True, default=lambda self: self.env.user.ho_id.id)
    parent_agent_id = fields.Many2one('tt.agent', 'Parent', required=True, default=lambda self: self.env.user.agent_id.id)
    email = fields.Char('Email', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string='Currency')

    def submit_customer_parent(self):
        cust_parent_obj = self.env['tt.customer.parent'].create({
            'name': self.name,
            'customer_parent_type_id': self.customer_parent_type_id.id,
            'ho_id': self.ho_id.id,
            'parent_agent_id': self.parent_agent_id.id,
            'email': self.email,
            'credit_limit': 0,
            'tax_percentage': 0.0,
        })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if {self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids)):
            action_num = self.env.ref('tt_base.tt_customer_parent_action_view').id
            menu_num = self.env.ref('tt_base.menu_customer_customer_parent').id
        else:
            action_num = self.env.ref('tt_base.tt_customer_parent_action_view_customer').id
            menu_num = self.env.ref('tt_base.menu_customers_customer_customer_parent').id

        return {
            'type': 'ir.actions.act_url',
            'name': cust_parent_obj.name,
            'target': 'self',
            'url': base_url + "/web#id=" + str(cust_parent_obj.id) + "&action=" + str(
                action_num) + "&model=tt.customer.parent&view_type=form&menu_id=" + str(menu_num),
        }
