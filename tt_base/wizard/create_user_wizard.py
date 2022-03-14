from odoo import api, fields, models, _


class CreateUserWizard(models.TransientModel):
    _name = "create.user.wizard"
    _description = 'Create User Wizard'

    user_template = fields.Many2one('res.users', 'User Template')

    def create_user(self):
        form_view_ref = self.env.ref('base.view_users_form', False)
        agent_id = self.env['tt.agent'].search([('id', '=', self._context['agent_id'])])

        # user_dict = self.user_template.read()
        default_groups_id = self.user_template.groups_id
        default_frontend_security_ids = self.user_template.frontend_security_ids
        vals = {
            'name': 'Create User',
            'res_model': 'res.users',
            'type': 'ir.actions.act_window',
            'views': [(form_view_ref.id, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'target': '_blank',
            'context': {
                'default_agent_id': agent_id.id,
            },
        }
        vals['context'].update({
            'default_groups_id': [(6, 0, default_groups_id.ids)],
            'default_frontend_security_ids': [(6, 0, default_frontend_security_ids.ids)]
        })
        return vals

class CreateCorporateUserWizard(models.TransientModel):
    _name = "create.corporate.user.wizard"
    _description = 'Create Corporate User Wizard'

    agent_id = fields.Many2one('tt.agent','Agent',readonly=True)
    customer_parent_id = fields.Many2one('tt.customer.parent','Customer Parent',readonly=True)

    def get_customer_domain(self):
        cust_booker_objs = self.env['tt.customer.parent.booker.rel'].search([('customer_parent_id', '=', self.customer_parent_id.id)])
        cust_dom_ids = []
        for rec_book in cust_booker_objs:
            if rec_book.customer_id.id not in cust_dom_ids:
                cust_dom_ids.append(rec_book.customer_id.id)
        return [('id','in',cust_dom_ids)]

    customer_id = fields.Many2one('tt.customer','Customer',domain=get_customer_domain)

    @api.onchange('customer_parent_id')
    def _onchange_domain_customer(self):
        return {'domain': {
            'customer_id': self.get_customer_domain()
        }}

    def create_cor_user(self):
        form_view_ref = self.env.ref('base.view_users_form', False)
        user_template = self.env['res.users'].browse(self.env.ref("tt_base.template_corpor_user_manager").id) # asumsi yg di buat corpor manager

        default_groups_id = user_template.groups_id
        default_frontend_security_ids = user_template.frontend_security_ids
        vals = {
            'name': 'Create User',
            'res_model': 'res.users',
            'type': 'ir.actions.act_window',
            'views': [(form_view_ref.id, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'target': '_blank',
            'context': {
                'default_agent_id': self.agent_id.id,
                'default_customer_parent_id': self.customer_parent_id.id,
                'default_customer_id': self.customer_id.id,
            },
        }
        vals['context'].update({
            'default_groups_id': [(6, 0, default_groups_id.ids)],
            'default_frontend_security_ids': [(6, 0, default_frontend_security_ids.ids)]
        })
        return vals
    #
    # def create_user_corp(self):
    #     new_user = self.env.ref('template_corpor_user_manager').copy()
    #     new_user.name = self.name,
    #     new_user.login = self.login
    #
    #     return {
    #
    #     }
    #     # return {
    #     #     'type': 'ir.actions.act_url',
    #     #     'name': cust_parent_obj.name,
    #     #     'target': 'self',
    #     #     'url': base_url + "/web#id=" + str(cust_parent_obj.id) + "&action=" + str(
    #     #         action_num) + "&model=tt.refund&view_type=form&menu_id=" + str(menu_num),
    #     # }