from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
import math

_logger = logging.getLogger(__name__)


class TtMasterAdminFee(models.Model):
    _inherit = 'tt.history'
    _name = "tt.master.admin.fee"
    _description = 'Master Admin Fee'
    _order = 'sequence, id desc'

    display_name = fields.Char('Display Name', compute='_compute_display_name')
    name = fields.Char('Description')
    after_sales_type = fields.Selection([('after_sales', 'After Sales'), ('refund', 'Refund'), ('offline', 'Issued Offline')], 'Transaction Type', default='after_sales')
    refund_type_id = fields.Many2one('tt.refund.type', 'Refund Type', required=False)
    min_amount_ho = fields.Float('Minimum Amount (HO)', default=0)
    min_amount_agent = fields.Float('Minimum Amount (Agent)', default=0)
    agent_type_ids = fields.Many2many('tt.agent.type', 'master_admin_fee_agent_type_rel', 'admin_fee_id', 'agent_type_id', string='Agent Types')
    agent_type_access_type = fields.Selection([("all", "ALL"),("allow", "Allowed"),("restrict", "Restricted")], 'Agent Type Access Type', default='all')
    agent_ids = fields.Many2many('tt.agent', 'master_admin_fee_agent_rel', 'admin_fee_id', 'agent_id', string='Agents')
    agent_access_type = fields.Selection([("all", "ALL"),("allow", "Allowed"),("restrict", "Restricted")], 'Agent Access Type', default='all')
    customer_parent_type_ids = fields.Many2many('tt.customer.parent.type', 'master_admin_fee_customer_parent_type_rel', 'admin_fee_id','customer_parent_type_id', string='Customer Parent Types')
    customer_parent_type_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Customer Parent Type Access Type', default='all')
    customer_parent_ids = fields.Many2many('tt.customer.parent', 'master_admin_fee_customer_parent_rel', 'admin_fee_id', 'customer_parent_id', string='Customer Parents')
    customer_parent_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Customer Parent Access Type', default='all')
    provider_type_ids = fields.Many2many('tt.provider.type', 'admin_fee_provider_type_rel', 'admin_fee_id', 'provider_type_id', string='Provider Types')
    provider_type_access_type = fields.Selection([("all", "ALL"),("allow", "Allowed"),("restrict", "Restricted")], 'Provider Type Access Type', default='all', required=True)
    admin_fee_line_ids = fields.One2many('tt.master.admin.fee.line', 'master_admin_fee_id', 'Admin Fee Line(s)')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    sequence = fields.Integer('Sequence', default=50)
    active = fields.Boolean('Active', default=True)

    @api.multi
    def write(self, vals):
        if not ({self.env.ref('tt_base.group_after_sales_master_level_2').id,
                 self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            for rec in list(vals.keys()):
                if rec not in ['sequence', 'customer_parent_type_access_type', 'customer_parent_type_ids', 'customer_parent_access_type', 'customer_parent_ids']:
                    vals.pop(rec)
        return super(TtMasterAdminFee, self).write(vals)

    @api.depends('after_sales_type', 'refund_type_id', 'provider_type_access_type', 'provider_type_ids', 'agent_type_access_type', 'agent_type_ids', 'agent_access_type', 'agent_ids', 'customer_parent_type_access_type', 'customer_parent_type_ids', 'customer_parent_access_type', 'customer_parent_ids')
    @api.onchange('after_sales_type', 'refund_type_id', 'provider_type_access_type', 'provider_type_ids', 'agent_type_access_type', 'agent_type_ids', 'agent_access_type', 'agent_ids', 'customer_parent_type_access_type', 'customer_parent_type_ids', 'customer_parent_access_type', 'customer_parent_ids')
    def _compute_display_name(self):
        for rec in self:
            temp_disp_name = '%s' % dict(self._fields['after_sales_type'].selection).get(rec.after_sales_type)

            provider_type_name = 'For All Provider Types'
            if rec.provider_type_access_type != 'all':
                name_list = []
                for provider_type in rec.provider_type_ids:
                    name_list.append('%s' % provider_type.name)
                provider_type_name = '%s For Provider Type(s) %s' % (rec.provider_type_access_type.title(), ','.join(name_list))
            temp_disp_name += ' (%s)' % provider_type_name

            agent_type_name = 'For All Agent Types'
            if rec.agent_type_access_type != 'all':
                name_list = []
                for agent_type in rec.agent_type_ids:
                    name_list.append('%s' % agent_type.name)
                agent_type_name = '%s For Agent Type(s) %s' % (rec.agent_type_access_type.title(), ','.join(name_list))
            temp_disp_name += ' (%s)' % agent_type_name

            agent_name = 'For All Agents'
            if rec.agent_access_type != 'all':
                name_list = []
                for agent in rec.agent_ids:
                    name_list.append('%s' % agent.name)
                agent_name = '%s For Agent(s) %s' % (rec.agent_access_type.title(), ','.join(name_list))
            temp_disp_name += ' (%s)' % agent_name

            customer_parent_type_name = 'For All Customer Parent Types'
            if rec.customer_parent_type_access_type != 'all':
                name_list = []
                for customer_parent_type in rec.customer_parent_type_ids:
                    name_list.append('%s' % customer_parent_type.name)
                customer_parent_type_name = '%s For Customer Parent Type(s) %s' % (rec.customer_parent_type_access_type.title(), ','.join(name_list))
            temp_disp_name += ' (%s)' % customer_parent_type_name

            customer_parent_name = 'For All Customer Parents'
            if rec.customer_parent_access_type != 'all':
                name_list = []
                for customer_parent in rec.customer_parent_ids:
                    name_list.append('%s' % customer_parent.name)
                customer_parent_name = '%s For Customer Parent(s) %s' % (rec.customer_parent_access_type.title(), ','.join(name_list))
            temp_disp_name += ' (%s)' % customer_parent_name

            rec.display_name = temp_disp_name

    def get_final_adm_fee_ho(self, total=0, pnr_multiplier=1, pax_multiplier=1, journey_multiplier=1):
        final_amt = 0
        for rec in self.admin_fee_line_ids:
            if rec.balance_for == 'ho':
                if rec.is_per_pnr and rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier * pnr_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier * pnr_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_journey and rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier * journey_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier * journey_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_pnr:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pnr_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pnr_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_journey:
                    if rec.type == 'amount':
                        final_amt += rec.amount * journey_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * journey_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier
                        final_amt += math.ceil(result)

                else:
                    if rec.type == 'amount':
                        final_amt += rec.amount
                    else:
                        result = (rec.amount / 100.0) * total
                        final_amt += math.ceil(result)

        if final_amt < self.min_amount_ho:
            final_amt = self.min_amount_ho

        return final_amt

    def get_final_adm_fee_agent(self, total=0, pnr_multiplier=1, pax_multiplier=1, journey_multiplier=1):
        final_amt = 0
        for rec in self.admin_fee_line_ids:
            if rec.balance_for == 'agent':
                if rec.is_per_pnr and rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier * pnr_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier * pnr_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_journey and rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier * journey_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier * journey_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_pnr:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pnr_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pnr_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_journey:
                    if rec.type == 'amount':
                        final_amt += rec.amount * journey_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * journey_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier
                        final_amt += math.ceil(result)

                else:
                    if rec.type == 'amount':
                        final_amt += rec.amount
                    else:
                        result = (rec.amount / 100.0) * total
                        final_amt += math.ceil(result)

        if final_amt < self.min_amount_agent:
            final_amt = self.min_amount_agent

        return final_amt

    def copy_setup(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 469')
        new_setup_obj = self.copy()

        for rec in self.admin_fee_line_ids:
            self.env['tt.master.admin.fee.line'].create({
                'master_admin_fee_id': new_setup_obj.id,
                'type': rec.type,
                'amount': rec.amount,
                'is_per_pnr': rec.is_per_pnr,
                'is_per_pax': rec.is_per_pax,
                'is_per_journey': rec.is_per_journey,
                'balance_for': rec.balance_for
            })

        provider_type_ids_list = []
        for rec in self.provider_type_ids:
            provider_type_ids_list.append(rec.id)

        agent_type_ids_list = []
        for rec in self.agent_type_ids:
            agent_type_ids_list.append(rec.id)

        agent_ids_list = []
        for rec in self.agent_ids:
            agent_ids_list.append(rec.id)

        customer_parent_type_ids_list = []
        for rec in self.customer_parent_type_ids:
            customer_parent_type_ids_list.append(rec.id)

        customer_parent_ids_list = []
        for rec in self.customer_parent_ids:
            customer_parent_ids_list.append(rec.id)

        new_setup_obj.write({
            'provider_type_ids': provider_type_ids_list,
            'agent_type_ids': agent_type_ids_list,
            'agent_ids': agent_ids_list,
            'customer_parent_type_ids': customer_parent_type_ids_list,
            'customer_parent_ids': customer_parent_ids_list
        })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_num = self.env.ref('tt_accounting.tt_master_admin_fee_action_views').id
        menu_num = self.env.ref('tt_accounting.sub_menu_tour_travel_master_admin_fee').id
        return {
            'type': 'ir.actions.act_url',
            'name': new_setup_obj.name,
            'target': 'self',
            'url': base_url + "/web#id=" + str(new_setup_obj.id) + "&action=" + str(
                action_num) + "&model=tt.master.admin.fee&view_type=form&menu_id=" + str(menu_num),
        }


class TtAgent(models.Model):
    _inherit = 'tt.agent'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'master_admin_fee_agent_rel', 'agent_id', 'admin_fee_id', string='Admin Fee')


class TtAgentType(models.Model):
    _inherit = 'tt.agent.type'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'master_admin_fee_agent_type_rel', 'agent_type_id', 'admin_fee_id', string='Admin Fee')


class TtCustomerParent(models.Model):
    _inherit = 'tt.customer.parent'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'master_admin_fee_customer_parent_rel', 'customer_parent_id', 'admin_fee_id', string='Admin Fee')


class TtCustomerParentType(models.Model):
    _inherit = 'tt.customer.parent.type'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'master_admin_fee_customer_parent_type_rel', 'customer_parent_type_id', 'admin_fee_id', string='Admin Fee')


class TtProviderType(models.Model):
    _inherit = 'tt.provider.type'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'admin_fee_provider_type_rel', 'provider_type_id', 'admin_fee_id', string='Admin Fee')


class TtMasterAdminFeeLine(models.Model):
    _name = "tt.master.admin.fee.line"
    _description = 'Master Admin Fee Line'
    _rec_name = 'amount'

    type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], 'Type', default='amount')
    amount = fields.Integer('Amount', default=0)
    is_per_pnr = fields.Boolean('Is Per PNR', default=True)
    is_per_pax = fields.Boolean('Is Per Pax', default=True)
    is_per_journey = fields.Boolean('Is Per Journey', default=False)
    balance_for = fields.Selection([('ho', 'Head Office'), ('agent', 'Agent')], 'Balance For', default='ho')
    master_admin_fee_id = fields.Many2one('tt.master.admin.fee', 'Master Admin Fee')

    @api.onchange("is_per_pnr")
    def _compute_per_pnr(self):
        if self.is_per_pnr:
            self.is_per_journey = False

    @api.onchange("is_per_journey")
    def _compute_per_journey(self):
        if self.is_per_journey:
            self.is_per_pnr = False
