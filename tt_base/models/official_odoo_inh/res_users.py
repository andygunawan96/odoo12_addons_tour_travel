from odoo import api, fields, models, _, SUPERUSER_ID
from ....tools.db_connector import GatewayConnector
from odoo.exceptions import UserError, AccessDenied
import time,re
import logging, traceback, pytz
from ....tools.ERR import RequestException
from ....tools import ERR
from odoo.http import request
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

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

    signup_token = fields.Char(copy=False, groups="base.group_erp_manager, tt_base.group_user_data_level_3")
    signup_type = fields.Char(string='Signup Token Type', copy=False,
                              groups="base.group_erp_manager, tt_base.group_user_data_level_3")
    signup_expiration = fields.Datetime(copy=False,
                                        groups="base.group_erp_manager, tt_base.group_user_data_level_3")

    @api.model
    def signup_retrieve_info(self, token):
        # Tdk di inherit kren func _signup_retrieve_partner cll once only
        partner = self._signup_retrieve_partner(token, raise_exception=True)
        res = {'db': self.env.cr.dbname}
        if partner.signup_valid:
            res['token'] = token
            res['name'] = partner.name
        if partner.user_ids:
            res['login'] = partner.user_ids[0].login
            # Extended p4rt st4rt
            # res['is_need_otp'] = partner.user_ids[0].is_using_otp
            # Extended p4rt end
        else:
            res['email'] = res['login'] = partner.email or ''
        return res


class ResUsers(models.Model):
    _inherit = 'res.users'

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True, required=False, default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)
    agent_type_related_id = fields.Many2one('tt.agent.type','Agent Related Type', related='agent_id.agent_type_id')
    transaction_limit = fields.Monetary('Transaction Limit')
    agent_type_id = fields.Many2one('tt.agent.type', 'Template For Agent Type', help="Agent Type Template")
    is_user_template = fields.Boolean('Is User Template', default=False)
    vendor_id = fields.Many2one('tt.vendor', 'External Vendor')

    ##security section
    is_using_otp = fields.Boolean('Is Using OTP', default=False)
    machine_ids = fields.Many2many('tt.machine', 'tt_machine_split_rel', 'machine_id', 'res_user_id', 'Machine IDs', readonly=True)
    is_using_pin = fields.Boolean("Is Using Pin", default=False)
    pin_log_ids = fields.One2many('tt.pin.log', 'user_id', 'Pin Log IDs', readonly=True)
    pin = fields.Char("PIN", compute='_compute_pin', inverse='_set_pin', invisible=True, copy=False, store=True)

    def _compute_pin(self):
        for user in self:
            user.pin = ''

    def _set_pin(self):
        ctx = self._crypt_context()
        for user in self:
            self._set_encrypted_pin(user.id, ctx.encrypt(user.pin))

    def _set_encrypted_pin(self, uid, pin):
        assert self._crypt_context().identify(pin) != 'plaintext'

        self.env.cr.execute(
            'UPDATE res_users SET pin=%s WHERE id=%s',
            (pin, uid)
        )
        self.invalidate_cache(['pin'], [uid])

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

        try:
            data = {
                'code': 9901,
                'title': 'USER CREATED',
                'message': 'New User Created: %s\nBy: %s\n' % (
                    new_user.name, self.env.user.name)
            }
            context = {
                "co_ho_id": new_user.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "create user" telegram notification: ' + str(e))
        return new_user

    @api.multi
    def write(self, vals):
        admin_obj_id = self.env.ref('base.user_admin').id
        root_obj_id = self.env.ref('base.user_root').id
        if not self.env.user.id in [admin_obj_id, root_obj_id] and (self.id in [admin_obj_id, root_obj_id] or (self.has_group('base.group_system') and not self.env.user.has_group('base.group_system')) or (self.has_group('base.group_erp_manager') and not self.env.user.has_group('base.group_erp_manager'))):
            raise UserError('You do not have permission to edit this record.')
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
            elif keys_to_check.get('ho') and not self.has_group('tt_base.group_tt_agent_user') and not is_set_agent and not self.has_group('tt_base.group_tt_corpor_user') and not is_set_corpor:
                vals.pop(keys_to_check['ho'])
            elif keys_to_check.get('agent') and not self.has_group('tt_base.group_tt_tour_travel') and not is_set_ho and not self.has_group('tt_base.group_tt_corpor_user') and not is_set_corpor:
                vals.pop(keys_to_check['agent'])
            elif keys_to_check.get('corpor') and not self.has_group('tt_base.group_tt_tour_travel') and not is_set_ho and not self.has_group('tt_base.group_tt_agent_user') and not is_set_agent:
                vals.pop(keys_to_check['corpor'])
        if 'is_using_pin' in vals and not self.env.user.has_group('base.group_system'):
            vals.pop('is_using_pin')
        if 'is_using_otp' in vals:
            # kalau tidak punya admin atau user data level 5 tidak bisa edit field ini
            if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_user_data_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
                vals.pop('is_using_otp')
            # kalau bukan admin tidak bisa mematikan OTP
            elif not self.env.user.has_group('base.group_system') and not vals['is_using_otp']:
                vals.pop('is_using_otp')
        if 'is_banned' in vals:
            # kalau tidak punya admin atau user data level 5 tidak bisa edit field ini
            if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_user_data_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
                vals.pop('is_banned')
        if vals.get('password'):
            self._check_password(vals['password'])

            if self.is_using_otp:
                self.check_need_otp_user_api({
                    'machine_code': vals.get('machine_code'),
                    'otp': vals.get('otp'),
                    'platform': vals.get('platform'),
                    'browser': vals.get('browser'),
                    'timezone': vals.get('timezone'),
                    'otp_type': vals.get('otp_type', ''),
                    'is_resend_otp': vals.get('is_resend_otp', False),
                })
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

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env, otp_params=False):
        """Verifies and returns the user ID corresponding to the given
          ``login`` and ``password`` combination, or False if there was
          no matching user.
           :param str db: the database on which user is trying to authenticate
           :param str login: username
           :param str password: user password
           :param dict user_agent_env: environment dictionary describing any
               relevant environment attributes
        """
        uid = cls._login(db, login, password, otp_params=otp_params)
        if user_agent_env and user_agent_env.get('base_location'):
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, uid, {})
                if env.user.has_group('base.group_system'):
                    # Successfully logged in as system user!
                    # Attempt to guess the web base url...
                    try:
                        base = user_agent_env['base_location']
                        ICP = env['ir.config_parameter']
                        if not ICP.get_param('web.base.url.freeze'):
                            ICP.set_param('web.base.url', base)
                    except Exception:
                        _logger.exception("Failed to update web.base.url configuration parameter")
        return uid

    @classmethod
    def _login(cls, db, login, password, otp_params=False):
        if not password:
            raise AccessDenied()
        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        try:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                with self._assert_can_auth():
                    user = self.search(self._get_login_domain(login))
                    if not user:
                        raise AccessDenied()
                    user = user.sudo(user.id)
                    if user.is_banned:
                        raise RequestException(4030)

                    user._check_credentials(password, otp_params=otp_params)
                    user._update_last_login()
        except RequestException as e:
            _logger.info("Fail on Login Check, %s" % (str(e)))
            raise e
        except AccessDenied:
            _logger.info("Login failed for db:%s login:%s from %s", db, login, ip)
            raise

        _logger.info("Login successful for db:%s login:%s from %s", db, login, ip)

        return user.id

    def _check_credentials(self, password, otp_params=False):
        super(ResUsers,self)._check_credentials(password)
        if self.is_using_otp:
            if not otp_params:
                raise RequestException(1041)
            self.check_need_otp_user_api({
                'machine_code': otp_params.get('machine_code'),
                'otp': otp_params.get('otp'),
                'platform': otp_params.get('platform'),
                'browser': otp_params.get('browser'),
                'timezone': otp_params.get('timezone'),
                'otp_type': otp_params.get('otp_type', False),
                'is_resend_otp': otp_params.get('is_resend_otp', False),
            })

    def _check_pin(self, pin):
        if not pin:
            raise RequestException(1042)

        self.env.cr.execute(
            "SELECT COALESCE(pin, '') FROM res_users WHERE id=%s",
            [self.id]
        )
        [hashed] = self.env.cr.fetchone()
        valid, replacement = self._crypt_context()\
            .verify_and_update(pin, hashed)
        if replacement is not None:
            self._set_encrypted_pin(self.env.user.id, replacement)
        if not valid:
            raise RequestException(1042)


    def check_pin_api(self, purpose_type, pin):
        try:
            if self.is_banned:
                raise RequestException(4030)
            self._check_pin(pin)
            if purpose_type == 'check':
                purpose_type = 'correct'
            self.env['tt.pin.log'].create_pin_log(self, purpose_type)
        except RequestException as e:
            self.env['tt.pin.log'].create_pin_log(self, 'wrong')
            raise e

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

    def turn_on_pin_api(self, data, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        user_obj.pin = data['pin']
        user_obj.is_using_pin = True
        self.env['tt.pin.log'].create_pin_log(user_obj, 'set')
        return ERR.get_no_error()

    def turn_off_pin_api(self, data, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        user_obj.check_pin_api('turn_off', data['pin'])
        user_obj.pin = ''
        user_obj.is_using_pin = False
        return ERR.get_no_error()

    def change_pin_otp_api(self, data, context):
        user_obj = self.browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)
        if data.get('otp_params'):
            if not user_obj.is_using_otp:
                raise RequestException(1043)
            data['otp_params']['change_pin'] = True
            otp_obj = user_obj.create_or_get_otp_user_api(data['otp_params'])
            raise RequestException(1040, additional_message=(otp_obj.create_date + timedelta(minutes=user_obj.ho_id.otp_expired_time)).strftime('%Y-%m-%d %H:%M:%S'))
        else:
            raise RequestException(1044)

    def change_pin_api(self, data, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        if data.get('otp_params'):
            now = datetime.now()
            otp_objs = self.env['tt.otp'].search([
                ('machine_id.code', '=', data['otp_params']['machine_code']),
                ('otp', '=', data['otp_params']['otp']),
                ('purpose_type', '=', 'change_pin'),
                ('is_connect', '=', False),
                ('user_id','=',user_obj.id),
                ('create_date', '>', now - timedelta(minutes=user_obj.ho_id.otp_expired_time))
            ])
            if otp_objs:
                notes = ['Forgot pin, Change PIN using this OTP']
                for otp_obj in otp_objs:
                    otp_obj.update({
                        "is_connect": True,
                        "is_disconnect": True,
                        "connect_date": now,
                        "disconnect_date": now,
                        'description': "\n".join(notes)
                    })
                self.env['tt.pin.log'].create_pin_log(user_obj, 'change_by_otp')
            else:
                self.env['tt.pin.log'].create_pin_log(user_obj, 'wrong')
                return ERR.get_error(1041)
        else:
            user_obj.check_pin_api('change', data['old_pin'])
        user_obj.pin = data['pin']
        return ERR.get_no_error()


    def delete_user_api(self, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)
        ## HANYA DI OPEN UNTUK AGENT BTC
        if user_obj.ho_id.btc_agent_type_id == user_obj.agent_id.agent_type_id:
            ### DELETE USER
            user_seq_id = self.env['ir.sequence'].next_by_code('deleted.res.users.seq')
            notif_string = 'From %s to %s by user request' % (user_obj.name, user_seq_id)
            user_obj.login = user_seq_id
            user_obj.name = user_seq_id
            ### DELETE AGENT JIKA USER HANYA ADA YG AKAN DI INACTIVE SAJA
            if len(user_obj.user_ids.ids) == 1:
                user_obj.agent_id.name = self.env['ir.sequence'].next_by_code('deleted.tt.agent.seq')
            user_obj.active = False

            data = {
                'code': 9909,
                'title': 'Inactive User',
                'message': notif_string
            }
            context = {
                "co_ho_id": context['co_ho_id']
            }
            GatewayConnector().telegram_notif_api(data, context)

            return ERR.get_no_error()
        else:
            data = {
                'code': 9909,
                'title': 'Inactive User',
                'message': '%s is trying to delete account by user request' % user_obj.name
            }
            context = {
                "co_ho_id": context['co_ho_id']
            }
            GatewayConnector().telegram_notif_api(data, context)

            return ERR.get_error(500, additional_message='Please contact Admin to delete account!')

    def get_machine_otp_pin(self):
        res = {
            "co_is_using_otp": self.is_using_otp,
            'co_otp_list_machine': [],
            'co_is_using_pin': self.is_using_pin,
            'co_ho_is_using_pin': self.ho_id.is_agent_required_pin,
            'co_ho_is_using_otp': self.ho_id.is_agent_required_otp
        }
        if self.is_using_otp:
            otp_objs = self.env['tt.otp'].search([
                ('user_id.id', '=', self.id),
                ('is_connect', '=', True),
                ('is_disconnect', '=', False),
                ('purpose_type', '=', 'turn_on')
            ])
            for otp_obj in otp_objs:
                try:
                    is_need_add_otp = False
                    if otp_obj.duration and len(otp_obj.duration) == 1 and 49 <= ord(otp_obj.duration[0]) <= 57:
                        if otp_obj.create_date.replace(hour=0, minute=0, second=0,tzinfo=pytz.timezone('Asia/Jakarta')) + timedelta(days=int(otp_obj.duration)) > datetime.now(pytz.timezone('Asia/Jakarta')):
                            is_need_add_otp = True
                    elif otp_obj.duration == 'never':
                        is_need_add_otp = True
                    else:
                        is_need_add_otp = True
                    if is_need_add_otp:
                        res['co_otp_list_machine'].append({
                            "machine_id": otp_obj.machine_id.code,
                            "platform": otp_obj.platform,
                            "browser": otp_obj.browser,
                            "timezone": otp_obj.timezone,
                            "valid_date": (otp_obj.create_date.replace(hour=0,minute=0,second=0) + timedelta(days=int(otp_obj.duration))).strftime('%Y-%m-%d %H:%M:%S') if len(otp_obj.duration)==1 else otp_obj.duration,
                            "connect_date_utc": otp_obj.connect_date.strftime('%Y-%m-%d %H:%M:%S')
                        })
                except Exception as e:
                    _logger.error("%s, %s" % (str(e), traceback.format_exc()))
        return res
