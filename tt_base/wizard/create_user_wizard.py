from odoo import api, fields, models, _


class CreateUserWizard(models.TransientModel):
    _name = "create.user.wizard"
    _description = 'Create User Wizard'

    user_template = fields.Many2one('res.users', 'User Template')

    def create_user(self):
        form_view_ref = self.env.ref('base.view_users_form', False)
        agent_id = self.env['tt.agent'].search([('id', '=', self._context['agent_id'])])
        user_dict = self.user_template.read()
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
        if user_dict:
            vals['context'].update({
                'default_groups_id': [(6, 0, user_dict[0]['groups_id'])],
                'default_frontend_security_ids': [(6, 0, user_dict[0]['frontend_security_ids'])]
            })
        return vals
