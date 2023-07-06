from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time,re

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

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True, required=True, default=lambda self: self.env.user.ho_id.id)
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
        admin_obj_id = self.env.ref('base.user_admin').id
        root_obj_id = self.env.ref('base.user_root').id
        if vals.get('sel_groups_2_3'):
            if (vals['sel_groups_2_3'] == 3 and not self.env.user.id in [admin_obj_id, root_obj_id]) or (vals['sel_groups_2_3'] == 2 and not self.env.user.has_group('base.group_system')):
                vals.pop('sel_groups_2_3')
        if vals.get('groups_id'):
            if vals['groups_id'][0][0] == 6:
                list_to_check = vals['groups_id'][0][2]
                if 3 in list_to_check and not self.env.user.id in [admin_obj_id, root_obj_id]:
                    list_to_check.remove(3)
                if 2 in list_to_check and not self.env.user.has_group('base.group_system'):
                    list_to_check.remove(2)
                vals.update({
                    'groups_id': [(6,0,list_to_check)]
                })
            elif vals['groups_id'][0][0] == 4:
                if (vals['groups_id'][0][1] == 3 and not self.env.user.id in [admin_obj_id, root_obj_id]) or (vals['groups_id'][0][1] == 2 and not self.env.user.has_group('base.group_system')):
                    vals.pop('groups_id')
        if not self.env.user.has_group('base.group_erp_manager') and not self.env.user.id in [admin_obj_id, root_obj_id] and not vals.get('groups_id'): #jika tidak punya access rights tidak boleh create tanpa is HO and is Agent, harus ada salah satu
            ho_group_id = self.env.ref('tt_base.group_tt_tour_travel').id
            agent_group_id = self.env.ref('tt_base.group_tt_agent_user').id
            corpor_group_id = self.env.ref('tt_base.group_tt_corpor_user').id
            is_set_ho = False
            is_set_agent = False
            is_set_corpor = False
            for rec in vals.keys():
                if len(rec.split('sel_groups')) > 1 or len(rec.split('in_group')) > 1:
                    if str(ho_group_id) in rec.split('_') and vals[rec]:
                        is_set_ho = True
                    elif str(agent_group_id) in rec.split('_') and vals[rec]:
                        is_set_agent = True
                    elif str(corpor_group_id) in rec.split('_') and vals[rec]:
                        is_set_corpor = True
            if not is_set_ho and not is_set_agent and not is_set_corpor:
                raise UserError('Please set either "Is Tour Travel HO" or "Is Agent User" or "Is Corporate User"!')
        new_user = super(ResUsers, self).create(vals)
        # new_user.partner_id.parent_id = new_user.agent_id.id
        new_user.partner_id.parent_agent_id = False
        return new_user

    @api.multi
    def write(self, vals):
        admin_obj_id = self.env.ref('base.user_admin').id
        root_obj_id = self.env.ref('base.user_root').id
        if vals.get('sel_groups_2_3'):
            if (vals['sel_groups_2_3'] == 3 and not self.env.user.id in [admin_obj_id, root_obj_id]) or (vals['sel_groups_2_3'] == 2 and not self.env.user.has_group('base.group_system')):
                vals.pop('sel_groups_2_3')
        if vals.get('groups_id'):
            if vals['groups_id'][0][0] == 6:
                list_to_check = vals['groups_id'][0][2]
                if 3 in list_to_check and not self.env.user.id in [admin_obj_id, root_obj_id]:
                    list_to_check.remove(3)
                if 2 in list_to_check and not self.env.user.has_group('base.group_system'):
                    list_to_check.remove(2)
                vals.update({
                    'groups_id': [(6,0,list_to_check)]
                })
            elif vals['groups_id'][0][0] == 4:
                if (vals['groups_id'][0][1] == 3 and not self.env.user.id in [admin_obj_id, root_obj_id]) or (vals['groups_id'][0][1] == 2 and not self.env.user.has_group('base.group_system')):
                    vals.pop('groups_id')
        if 'password' in vals and self.id == admin_obj_id and not self.env.user.id in [admin_obj_id, root_obj_id]: #tidak boleh ganti pwd admin kalau bukan admin settings
            vals.pop('password')
        if not self.env.user.has_group('base.group_erp_manager') and not self.env.user.id in [admin_obj_id, root_obj_id] and not vals.get('groups_id'): #jika tidak punya access rights tidak boleh remove both is HO and is Agent, harus ada salah satu
            ho_group_id = self.env.ref('tt_base.group_tt_tour_travel').id
            agent_group_id = self.env.ref('tt_base.group_tt_agent_user').id
            corpor_group_id = self.env.ref('tt_base.group_tt_corpor_user').id
            keys_to_check = {
                'ho': '',
                'agent': '',
                'corpor': ''
            }
            is_set_ho = False
            is_set_agent = False
            is_set_corpor = False
            for rec in vals.keys():
                if len(rec.split('sel_groups')) > 1 or len(rec.split('in_group')) > 1:
                    if str(ho_group_id) in rec.split('_'):
                        if not vals[rec]:
                            keys_to_check.update({
                                'ho': rec
                            })
                        else:
                            is_set_ho = True
                    elif str(agent_group_id) in rec.split('_'):
                        if not vals[rec]:
                            keys_to_check.update({
                                'agent': rec
                            })
                        else:
                            is_set_agent = True
                    elif str(corpor_group_id) in rec.split('_'):
                        if not vals[rec]:
                            keys_to_check.update({
                                'corpor': rec
                            })
                        else:
                            is_set_corpor = True
            if keys_to_check.get('ho') and keys_to_check.get('agent') and keys_to_check.get('corpor'):
                vals.pop(keys_to_check['ho'])
                vals.pop(keys_to_check['agent'])
                vals.pop(keys_to_check['corpor'])
            elif keys_to_check.get('ho') and not self.has_group('tt_base.group_tt_agent_user') and not is_set_agent and not self.has_group('tt_base.tt_base.group_tt_corpor_user') and not is_set_corpor:
                vals.pop(keys_to_check['ho'])
            elif keys_to_check.get('agent') and not self.has_group('tt_base.group_tt_tour_travel') and not is_set_ho and not self.has_group('tt_base.tt_base.group_tt_corpor_user') and not is_set_corpor:
                vals.pop(keys_to_check['agent'])
            elif keys_to_check.get('corpor') and not self.has_group('tt_base.group_tt_tour_travel') and not is_set_ho and not self.has_group('tt_base.group_tt_agent_user') and not is_set_agent:
                vals.pop(keys_to_check['corpor'])
        if vals.get('password'):
            self._check_password(vals['password'])
        return super(ResUsers, self).write(vals)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.id == self.env.ref('base.user_admin').id:
                raise UserError('Cannot delete superadmin.')
        super(ResUsers, self).unlink()

    ## OVERRIDE OFFICIAL FUNCTION BEWARE
    @api.model
    def signup(self, values, token=None):
        """ signup a user, to either:
            - create a new user (no token), or
            - create a user for a partner (with token, but no user for partner), or
            - change the password of a user (with token, and existing user).
            :param values: a dictionary with field values that are written on user
            :param token: signup token (optional)
            :return: (dbname, login, password) for the signed up user
        """
        if token:
            # signup with a token: find the corresponding partner id
            partner = self.env['res.partner']._signup_retrieve_partner(token, check_validity=True, raise_exception=True)
            # invalidate signup token
            ## ORINGAL LINE OF PARTNER.WRITE SIGNUP TOKEN FALSE
            partner_user = partner.user_ids and partner.user_ids[0] or False

            # avoid overwriting existing (presumably correct) values with geolocation data
            if partner.country_id or partner.zip or partner.city:
                values.pop('city', None)
                values.pop('country_id', None)
            if partner.lang:
                values.pop('lang', None)

            if partner_user:
                # user exists, modify it according to values
                values.pop('login', None)
                values.pop('name', None)
                partner_user.write(values)
                if not partner_user.login_date:
                    partner_user._notify_inviter()
                partner.write({'signup_token': False, 'signup_type': False, 'signup_expiration': False})#PARTNER.WRITE TOKEN FALSE MOVED HERE
                return (self.env.cr.dbname, partner_user.login, values.get('password'))
            else:
                # user does not exist: sign up invited user
                values.update({
                    'name': partner.name,
                    'partner_id': partner.id,
                    'email': values.get('email') or values.get('login'),
                })
                if partner.company_id:
                    values['company_id'] = partner.company_id.id
                    values['company_ids'] = [(6, 0, [partner.company_id.id])]
                partner_user = self._signup_create_user(values)
                partner_user._notify_inviter()
                partner.write({'signup_token': False, 'signup_type': False, 'signup_expiration': False})#PARTNER.WRITE TOKEN FALSE MOVED HERE

        else:
            # no token, sign up an external user
            values['email'] = values.get('email') or values.get('login')
            self._signup_create_user(values)

        return (self.env.cr.dbname, values.get('login'), values.get('password'))


    ##password_security OCA
    @api.multi
    def _check_password(self, password):
        self._check_password_rules(password)
        return True

    @api.multi
    def _check_password_rules(self, password):
        self.ensure_one()
        if not password:
            return True
        password_regex = [
            '^',
            '(?=.*?[a-z]){1,}',
            '(?=.*?[A-Z]){1,}',
            '(?=.*?\\d){1,}',
            r'(?=.*?[\W_]){1,}',
            '.{%d,}$' % 8,
        ]
        if not re.search(''.join(password_regex), password):
            raise UserError(self.password_match_message())

        return True

    @api.multi
    def password_match_message(self):
        self.ensure_one()
        message = 'Password must be 8 characters or more. Must also contain Lowercase letter, Uppercase letter, Numeric digit, Special character'
        return message
    ## OCA

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
