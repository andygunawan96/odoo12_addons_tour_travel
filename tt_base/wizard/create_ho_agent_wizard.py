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
    sub_agent_name = fields.Char('Initial Sub Agent Name', required=True)
    sub_agent_email = fields.Char('Initial Sub Agent Email')
    sub_agent_currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id, string='Initial Sub Agent Currency')
    sub_agent_type_name = fields.Char('Initial Sub Agent Type Name', required=True)
    sub_agent_type_code = fields.Char('Initial Sub Agent Type Code', required=True)
    sub_agent_type_seq_prefix = fields.Char('Initial Sub Agent Type Seq Prefix', size=2, required=True)

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

        sub_agent_type_obj = self.env['tt.agent.type'].create({
            'name': self.sub_agent_type_name,
            'code': self.sub_agent_type_code,
            'seq_prefix': self.sub_agent_type_seq_prefix,
            'ho_id': new_ho_obj.id
        })

        sub_agent_obj = self.env['tt.agent'].create({
            'name': self.sub_agent_name,
            'currency_id': self.sub_agent_currency_id.id,
            'email': self.sub_agent_email,
            'agent_type_id': sub_agent_type_obj.id,
            'ho_id': new_ho_obj.id,
            'parent_agent_id': new_ho_obj.id
        })

        regular_refund_adm = self.env['tt.master.admin.fee'].create({
            'name': 'Regular Refund',
            'after_sales_type': 'refund',
            'refund_type_id': self.env.ref('tt_accounting.refund_type_regular_refund').id,
            'min_amount_ho': 0,
            'min_amount_agent': 0,
            'agent_type_access_type': 'all',
            'agent_access_type': 'all',
            'provider_type_access_type': 'all',
            'ho_id': new_ho_obj.id,
            'sequence': 500
        })
        self.env['tt.master.admin.fee.line'].create({
            'type': 'amount',
            'amount': 50000,
            'is_per_pnr': True,
            'is_per_pax': True,
            'balance_for': 'ho',
            'master_admin_fee_id': regular_refund_adm.id
        })

        quick_refund_adm = self.env['tt.master.admin.fee'].create({
            'name': 'Quick Refund',
            'after_sales_type': 'refund',
            'refund_type_id': self.env.ref('tt_accounting.refund_type_quick_refund').id,
            'min_amount_ho': 0,
            'min_amount_agent': 0,
            'agent_type_access_type': 'all',
            'agent_access_type': 'all',
            'provider_type_access_type': 'all',
            'ho_id': new_ho_obj.id,
            'sequence': 501
        })
        self.env['tt.master.admin.fee.line'].create({
            'type': 'percentage',
            'amount': 5,
            'is_per_pnr': True,
            'is_per_pax': True,
            'balance_for': 'ho',
            'master_admin_fee_id': quick_refund_adm.id
        })

        reschedule_adm = self.env['tt.master.admin.fee'].create({
            'name': 'Reschedule',
            'after_sales_type': 'after_sales',
            'min_amount_ho': 0,
            'min_amount_agent': 0,
            'agent_type_access_type': 'all',
            'agent_access_type': 'all',
            'provider_type_access_type': 'all',
            'ho_id': new_ho_obj.id,
            'sequence': 500
        })
        self.env['tt.master.admin.fee.line'].create({
            'type': 'amount',
            'amount': 50000,
            'is_per_pnr': True,
            'is_per_pax': True,
            'balance_for': 'ho',
            'master_admin_fee_id': reschedule_adm.id
        })

        offline_adm = self.env['tt.master.admin.fee'].create({
            'name': 'Issued Offline',
            'after_sales_type': 'offline',
            'min_amount_ho': 0,
            'min_amount_agent': 0,
            'agent_type_access_type': 'all',
            'agent_access_type': 'all',
            'provider_type_access_type': 'all',
            'ho_id': new_ho_obj.id,
            'sequence': 500
        })
        self.env['tt.master.admin.fee.line'].create({
            'type': 'amount',
            'amount': 5000,
            'is_per_pnr': True,
            'is_per_pax': True,
            'balance_for': 'ho',
            'master_admin_fee_id': offline_adm.id
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

        # template ho system manager
        self.env['res.users'].create({
            'name': 'Template HO System Manager (%s)' % self.agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_ho_user_system_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': new_ho_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_ho_user_system_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_ho_user_system_manager').frontend_security_ids.ids)]
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

        # template ho btbo api
        self.env['res.users'].create({
            'name': 'Template HO BTBO User API (%s)' % self.agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_ho_btbo_user_api_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': new_ho_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_btbo_user_api').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_btbo_user_api').frontend_security_ids.ids)]
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
            'name': 'Template Agent Finance Manager (%s)' % self.sub_agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_agent_finance_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': sub_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_citra_agent_finance_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_citra_agent_finance_manager').frontend_security_ids.ids)]
        })

        # template agent manager
        self.env['res.users'].create({
            'name': 'Template Agent Manager (%s)' % self.sub_agent_type_name,
            'ho_id': new_ho_obj.id,
            'login': 'template_agent_user_manager_%s%s' % (datetime.now().strftime('%m%d%M%S'), str(btc_agent_obj.id)),
            'is_user_template': True,
            'agent_type_id': sub_agent_type_obj.id,
            'groups_id': [(6, 0, self.env.ref('tt_base.template_citra_agent_user_manager').groups_id.ids)],
            'frontend_security_ids': [(6, 0, self.env.ref('tt_base.template_citra_agent_user_manager').frontend_security_ids.ids)]
        })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if self.env.user.agent_id.is_ho_agent:
            action_num = self.env.ref('tt_base.tt_agent_all_action_view').id
            menu_num = self.env.ref('tt_base.menu_tour_travel_agent').id
        else:
            action_num = self.env.ref('tt_base.tt_agent_customer_action_view').id
            menu_num = self.env.ref('tt_base.menu_tour_travel_agent').id

        return {
            'type': 'ir.actions.act_url',
            'name': new_ho_obj.name,
            'target': 'self',
            'url': base_url + "/web#id=" + str(new_ho_obj.id) + "&action=" + str(
                action_num) + "&model=tt.agent&view_type=form&menu_id=" + str(menu_num)
        }
