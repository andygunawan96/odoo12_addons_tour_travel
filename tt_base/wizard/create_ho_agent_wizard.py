from odoo import api, fields, models, _


class CreateHOAgentWizard(models.TransientModel):
    _name = "create.ho.agent.wizard"
    _description = 'Create HO Agent Wizard'

    name = fields.Char('Head Office Name', required=True)
    email = fields.Char('Head Office Email')
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id, string='Head Office Currency')
    btc_name = fields.Char('Default BTC Agent Name', required=True)
    btc_email = fields.Char('Default BTC Agent Email')
    btc_currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id, string='Default BTC Agent Currency')
    agent_type_name = fields.Char('Head Office Agent Type Name', required=True)
    agent_type_code = fields.Char('Head Office Agent Type Code', required=True)
    agent_type_seq_prefix = fields.Char('Head Office Agent Type Seq Prefix', size=2, required=True)
    btc_agent_type_name = fields.Char('Default BTC Agent Type Name', required=True)
    btc_agent_type_code = fields.Char('Default BTC Agent Type Code', required=True)
    btc_agent_type_seq_prefix = fields.Char('Default BTC Agent Type Seq Prefix', size=2, required=True)

    def submit_ho_agent(self):
        new_ho_agent_type_obj = self.env['tt.agent.type'].create({
            'name': self.agent_type_name,
            'code': self.agent_type_code,
            'seq_prefix': self.agent_type_seq_prefix,
            'is_using_invoice': True
        })

        new_ho_obj = self.env['tt.agent'].create({
            'name': self.name,
            'currency_id': self.currency_id.id,
            'email': self.email,
            'is_ho_agent': True,
            'agent_type_id': new_ho_agent_type_obj.id
        })

        new_ho_agent_type_obj.write({
            'ho_id': new_ho_obj.id
        })

        btc_agent_type_obj = self.env['tt.agent.type'].create({
            'name': self.btc_agent_type_name,
            'code': self.btc_agent_type_code,
            'seq_prefix': self.btc_agent_type_seq_prefix,
            'is_using_invoice': True,
            'is_send_email_issued': True,
            'is_send_email_booked': True,
            'ho_id': new_ho_obj.id
        })

        btc_agent_obj = self.env['tt.agent'].create({
            'name': self.btc_name,
            'currency_id': self.btc_currency_id.id,
            'email': self.btc_email,
            'agent_type_id': btc_agent_type_obj.id,
            'is_btc_agent': True,
            'ho_id': new_ho_obj.id
        })

        new_ho_obj.write({
            'btc_agent_type_id': btc_agent_type_obj.id
        })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if self.env.user.agent_id.is_ho_agent:
            action_num = self.env.ref('tt_base.tt_agent_all_action_view').id
            menu_num = self.env.ref('tt_base.submenu_tour_travel_all_agent').id
        else:
            action_num = self.env.ref('tt_base.tt_agent_customer_action_view').id
            menu_num = self.env.ref('tt_base.submenu_customers_all_agent').id

        return {
            'type': 'ir.actions.act_url',
            'name': new_ho_obj.name,
            'target': 'self',
            'url': base_url + "/web#id=" + str(new_ho_obj.id) + "&action=" + str(
                action_num) + "&model=tt.agent&view_type=form&menu_id=" + str(menu_num)
        }
