from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time

LANGUAGE = [
    ('ID', 'Bahasa Indonesia'),
    ('US', 'English (United States)'),
    ('GB', 'English (United Kingdom)'),
    ('DE', 'Germany'),
    ('ES', 'Espanol'),
    ('CHN', 'Chinese')
]

DATE_FORMAT = [
    ('format1', 'Tuesday, 12 February 2019'),
    ('format2', 'Tuesday, 12 February 19'),
    ('format3', 'Tuesday, 12 Feb 2019'),
    ('format4', 'Tuesday, 12 Feb 19'),
    ('format5', 'Tuesday, 12-02-2019'),
    ('format6', 'Tuesday, 12-02-19'),
    ('format7', 'Tue, 12 February 2019'),
    ('format8', 'Tue, 12 February 19'),
    ('format9', 'Tue, 12 Feb 2019'),
    ('format10', 'Tue, 12 Feb 19'),
    ('format11', 'Tue, 12-02-2019'),
    ('format12', 'Tue, 12-02-19')
]

TIME_FORMAT = [
    ('format1', '23:59:59'),
    ('format2', '23:59'),
    ('format3', '11:59:59 PM'),
    ('format4', '11:59 PM')
]

USER_TYPE = [
    ('b2b', 'Business to Business (B2B)'),
    ('b2c', 'Business to Customer (B2C)')
]

DEVICE_TYPE = [
    ('web', 'Web'),
    ('android', 'Mobile Android'),
    ('ios', 'Mobile iOS')
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    signup_token = fields.Char(copy=False, groups="base.group_erp_manager, tt_base.group_tt_agent_management_operator, tt_base.group_user_data_level_3")
    signup_type = fields.Char(string='Signup Token Type', copy=False,
                              groups="base.group_erp_manager, tt_base.group_tt_agent_management_operator, tt_base.group_user_data_level_3")
    signup_expiration = fields.Datetime(copy=False,
                                        groups="base.group_erp_manager, tt_base.group_tt_agent_management_operator, tt_base.group_user_data_level_3")


class ResUsers(models.Model):
    _inherit = 'res.users'

    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)
    agent_type_related_id = fields.Many2one('tt.agent.type','Agent Related Type', related='agent_id.agent_type_id')
    transaction_limit = fields.Monetary('Transaction Limit')
    agent_type_id = fields.Many2one('tt.agent.type', 'Template For Agent Type', help="Agent Type Template")
    is_user_template = fields.Boolean('Is User Template', default=False)

    customer_id = fields.Many2one('tt.customer', 'Customer')
    customer_parent_id = fields.Many2one('tt.customer.parent','Customer Parent')

    access_activity_ids = fields.One2many('tt.access.activity', 'user_id', 'Access Activities')
    language = fields.Selection(LANGUAGE, 'Language')
    currency_id = fields.Many2one('res.currency', 'Currency')
    date_format = fields.Selection(DATE_FORMAT, 'Date Format')
    time_format = fields.Selection(TIME_FORMAT, 'Time Format')
    user_type = fields.Selection(USER_TYPE, 'User Type')
    device_type = fields.Selection(DEVICE_TYPE, 'Device Type')

    ####security utk django
    frontend_security_ids = fields.Many2many('tt.frontend.security','res_users_frontend_rel','res_users_id','frontend_security_id','Frontend Securities')
    is_banned = fields.Boolean('Banned')

    # @api.depends('agent_id','agent_id.agent_type_id')
    # @api.onchange('agent_id','agent_id.agent_type_id')
    # def _compute_agent_type_related_id(self):
    #     for rec in self:
    #         rec.agent_type_related_id = rec.agent_id.agent_type_id

    # Fungsi ini perlu di lengkapi/disempurnakan
    # Tujuan : kalau res_pertner.parent_agent_id berubah maka user.agent_id ikut berubah
    @api.onchange('partner_id.parent_agent_id')
    @api.depends('partner_id.parent_agent_id')
    def _onchange_partner_id(self):
        self.agent_id = self.parent_id.parent_agent_id

    # @api.multi
    # def _compute_allowed_customer_ids(self):
    #     for rec in self:
    #         rec.allowed_customer_ids = [rec.partner_id.id, rec.agent_id.id] \
    #                                    + rec.agent_id.sub_agent_ids.ids

    @api.model
    def create(self, vals):
        if not vals.get('email'):
            vals['email'] = time.time()
        vals['notification_type'] = 'inbox'
        new_user = super(ResUsers, self).create(vals)
        # new_user.partner_id.parent_id = new_user.agent_id.id
        new_user.partner_id.parent_agent_id = False
        return new_user

    def write(self, vals):
        admin_obj_id = self.env.ref('base.user_admin').id
        if vals.get('sel_groups_2_3') == 3 and self.env.user.id != admin_obj_id:
            vals.pop('sel_groups_2_3')
        if 'password' in vals and self.id == admin_obj_id and self.env.user.id != admin_obj_id:
            vals.pop('password')
        return super(ResUsers, self).write(vals)
    
    def unlink(self):
        for rec in self:
            if rec.id == self.env.ref('base.user_admin').id:
                raise UserError('Cannot delete superadmin.')
        super(ResUsers, self).unlink()

    # 28 OKT 2020, comment IP log karena isinya 127.0.0.1
    # @api.model
    # def _update_last_login(self):
    #     super(ResUsers, self)._update_last_login()
    #     self.env['tt.access.activity'].sudo().create({
    #         'type': 'login',
    #         'user_id': self.id,
    #         # 'user_ip_add': request.httprequest.headers.environ.get('HTTP_X_REAL_IP'),
    #         'user_ip_add': request.httprequest.environ['REMOTE_ADDR'],
    #     })