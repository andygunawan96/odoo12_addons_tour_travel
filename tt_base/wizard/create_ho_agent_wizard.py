from odoo import api, fields, models, _
from datetime import datetime


class CreateHOAgentWizard(models.TransientModel):
    _name = "create.ho.agent.wizard"
    _description = 'Create HO Agent Wizard'

    name = fields.Char('Head Office Name', required=True)
    email = fields.Char('Head Office Email')
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id, string='Head Office Currency')
    redirect_url_signup = fields.Char('Redirect URL Signup', default='/', required=True)
    agent_type_name = fields.Char('Head Office Agent Type Name', required=True)
    agent_type_code = fields.Char('Head Office Agent Type Code', required=True)
    agent_type_seq_prefix = fields.Char('Head Office Agent Type Seq Prefix', size=2, required=True)
    btc_name = fields.Char('Default BTC Agent Name', required=True)
    btc_email = fields.Char('Default BTC Agent Email')
    btc_currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id, string='Default BTC Agent Currency')
    btc_agent_type_name = fields.Char('Default BTC Agent Type Name', required=True)
    btc_agent_type_code = fields.Char('Default BTC Agent Type Code', required=True)
    btc_agent_type_seq_prefix = fields.Char('Default BTC Agent Type Seq Prefix', size=2, required=True)
    child_name = fields.Char('Initial Child Agent Name', required=True)
    child_email = fields.Char('Initial Child Agent Email')
    child_currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id, string='Initial Child Agent Currency')
    child_agent_type_name = fields.Char('Initial Child Agent Type Name', required=True)
    child_agent_type_code = fields.Char('Initial Child Agent Type Code', required=True)
    child_agent_type_seq_prefix = fields.Char('Initial Child Agent Type Seq Prefix', size=2, required=True)

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
            'redirect_url_signup': self.redirect_url_signup,
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

        child_agent_type_obj = self.env['tt.agent.type'].create({
            'name': self.child_agent_type_name,
            'code': self.child_agent_type_code,
            'seq_prefix': self.child_agent_type_seq_prefix,
            'ho_id': new_ho_obj.id
        })

        child_agent_obj = self.env['tt.agent'].create({
            'name': self.child_name,
            'currency_id': self.child_currency_id.id,
            'email': self.child_email,
            'agent_type_id': child_agent_type_obj.id,
            'ho_id': new_ho_obj.id
        })

        # agent btc user
        self.env['res.users'].create({
            'name': self.btc_name + ' User',
            'ho_id': new_ho_obj.id,
            'agent_id': btc_agent_obj.id,
            'login': 'btc_user_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'groups_id': [(6, 0, self.env.ref('tt_base.agent_b2c_user').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.agent_b2c_user').frontend_security_ids.ids)]
        })

        # template ho ops manager
        self.env['res.users'].create({
            'name': 'Template HO Operational Manager (%s)' % self.agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_ho_user_operational_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': new_ho_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_ho_user_operational_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_ho_user_operational_manager').frontend_security_ids.ids)]
        })

        # template ho accounting manager
        self.env['res.users'].create({
            'name': 'Template HO Accounting Manager (%s)' % self.agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_ho_user_accounting_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': new_ho_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_ho_user_accounting_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_ho_user_accounting_manager').frontend_security_ids.ids)]
        })

        # template ho product manager
        self.env['res.users'].create({
            'name': 'Template HO All Product Management Manager (%s)' % self.agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_ho_user_all_product_management_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': new_ho_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_ho_user_all_product_management_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_ho_user_all_product_management_manager').frontend_security_ids.ids)]
        })

        # template ho btb manager
        self.env['res.users'].create({
            'name': 'Template HO BTB Manager (%s)' % self.agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_ho_user_btb_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': new_ho_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_ho_user_btb_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_ho_user_btb_manager').frontend_security_ids.ids)]
        })

        # template ho ticketing
        self.env['res.users'].create({
            'name': 'Template HO Ticketing Manager (%s)' % self.agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_ho_ticketing_user_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': new_ho_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_ho_ticketing_user_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_ho_ticketing_user_manager').frontend_security_ids.ids)]
        })

        # template btc user
        self.env['res.users'].create({
            'name': 'Template BTC Agent (%s)' % self.btc_agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_btc_agent_user_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': btc_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_btc_agent_user').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_btc_agent_user').frontend_security_ids.ids)]
        })

        # template agent finance manager
        self.env['res.users'].create({
            'name': 'Template Agent Finance Manager (%s)' % self.child_agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_agent_finance_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': child_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_citra_agent_finance_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_citra_agent_finance_manager').frontend_security_ids.ids)]
        })

        # template agent manager
        self.env['res.users'].create({
            'name': 'Template Agent Manager (%s)' % self.child_agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_agent_user_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': child_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_citra_agent_user_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_citra_agent_user_manager').frontend_security_ids.ids)]
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
