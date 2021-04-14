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