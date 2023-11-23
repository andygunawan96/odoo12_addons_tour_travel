from odoo import api, fields, models, _
from odoo.exceptions import UserError
import math
import random
from datetime import datetime, timedelta
from ...tools.ERR import RequestException
from ...tools import ERR
import pytz

class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    ## HO cuman boleh menyalakan, Admin boleh nyala mati
    def toggle_active_otp(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_user_data_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 466')
        if not self.env.user.has_group('base.group_system') and self.is_using_otp:
            raise UserError('You do not have permission to turn off OTP.')
        self.is_using_otp = not self.is_using_otp

    def check_need_otp_user_api(self, req):
        is_machine_connect = False
        ## NEED TEST
        if req.get('machine_code'):
            otp_objs = self.env['tt.otp'].sudo().search([ ## SUDO Needed, else login from backend will fail
                ('machine_id.code','=', req['machine_code']),
                ('user_id.id','=', self.id),
                ('purpose_type','=', 'turn_on'),
                ('is_connect','=', True),
                ('is_disconnect','=', False)
            ])
        else:
            otp_objs = []
        for otp_obj in otp_objs:
            if otp_obj.duration:
                # if otp_obj.need_otp_type == 'always': ## ALWAYS SKIP KARENA SELALU MINTA OTP
                #     is_machine_connect = False
                #     otp_obj.active = False
                if otp_obj.duration == 'never':
                    is_machine_connect = True
                elif len(otp_obj.duration) == 1 and 49 <= ord(otp_obj.duration[0]) <= 57: ## DAYS
                    if otp_obj.create_date.replace(hour=0,minute=0,second=0,tzinfo=pytz.timezone('Asia/Jakarta')) + timedelta(days=int(otp_obj.duration)) > datetime.now(pytz.timezone('Asia/Jakarta')):
                        is_machine_connect = True
                    else:
                        otp_obj.active = False
            else:
                is_machine_connect = True

        if self.is_using_otp and not is_machine_connect:
            self.check_otp_user_api(req)

    def create_or_get_otp_user_api(self, req):
        if not req.get('machine_code'):
            raise RequestException(1044)
        ho_obj = self.sudo().ho_id
        ## NEED TEST

        machine_objs = self.env['tt.machine'].sudo().search([
            ('code', '=', req['machine_code']),
            ('user_id.id', '=', self.id)
        ])

        if not machine_objs:
            machine_objs = [self.env['tt.machine'].sudo().create_or_get_machine_api(req)]
            self.sudo().machine_ids = [(4, machine_objs[0].id)]

        for machine_obj in machine_objs:
            purpose_type = 'turn_on'
            if req.get('turn_off_otp'):
                purpose_type = 'turn_off'
            if req.get('turn_off_machine_id'):
                purpose_type = 'turn_off_this_machine'
            if req.get('is_turn_off_other_machine'):
                purpose_type = 'turn_off_other_machine'
            if req.get('change_pin'):
                purpose_type = 'change_pin'
            otp_objs = machine_obj.otp_ids.filtered(lambda x:
                        x.create_date > datetime.now() - timedelta(minutes=ho_obj.otp_expired_time) and
                        x.purpose_type == purpose_type and x.is_connect == False and x.user_id.id == self.id)
            if otp_objs:
                if req.get('is_resend_otp'):
                    for otp_obj in otp_objs:
                        otp_obj.active = False
                    otp_objs = [self.env['tt.otp'].sudo().create_otp(self.id, purpose_type, machine_obj)]
                else:
                    return otp_objs[0]
            else:
                otp_objs = [self.env['tt.otp'].sudo().create_otp(self.id, purpose_type, machine_obj)]
            if req.get('turn_off_otp'):
                otp_objs[0].send_email_turn_off_otp()
            elif req.get('turn_off_machine_id') and req.get('is_turn_off_other_machine'):
                otp_objs[0].send_email_turn_off_other_machine()
            elif req.get('turn_off_machine_id'):
                otp_objs[0].send_email_turn_off_machine()
            elif req.get('change_pin'):
                otp_objs[0].send_email_change_pin()
            else:
                otp_objs[0].send_email_otp()
            self.env.cr.commit()
            return otp_objs[0]

    def check_otp_user_api(self, req):
        ho_obj = self.sudo().ho_id
        now = datetime.now()
        if req.get('otp'):
            ## NEED TEST

            otp_objs = self.env['tt.otp'].sudo().search([
                ('machine_id.code','=', req['machine_code']),
                ('otp','=', req['otp']),
                ('create_date','>', now - timedelta(minutes=ho_obj.otp_expired_time)),
                ('purpose_type','=', 'turn_on')
            ])

            if otp_objs:
                for otp_obj in otp_objs:
                    otp_obj.update({
                        "is_connect": True,
                        "connect_date": now,
                        "description": 'Turn On',
                        "duration": req['otp_type'] if req.get('otp_type') and req['otp_type'] != '' else 'never'
                    })
                return True
            raise RequestException(1041)

        else:
            ## NO OTP CODE CREATE
            otp_obj = self.create_or_get_otp_user_api(req)
            raise RequestException(1040, additional_message=(otp_obj.create_date + timedelta(minutes=ho_obj.otp_expired_time)).strftime('%Y-%m-%d %H:%M:%S'))

    def set_otp_user_api(self, req, context):
        user_obj = self.browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)
        ## NEED TEST
        otp_obj = user_obj.create_or_get_otp_user_api(req)
        return ERR.get_no_error((otp_obj.create_date + timedelta(minutes=user_obj.ho_id.otp_expired_time)).strftime('%Y-%m-%d %H:%M:%S'))

    def activation_otp_user_api(self, req, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        ## NEED TEST
        now = datetime.now()
        otp_objs = self.env['tt.otp'].search([
            ('machine_id.code', '=', req['machine_code']),
            ('otp', '=', req['otp']),
            ('create_date', '>', now - timedelta(minutes=user_obj.ho_id.otp_expired_time)),
            ('purpose_type','=', 'turn_on'),
            ('is_connect','=', False)
        ])
        if otp_objs:
            for otp_obj in otp_objs:
                otp_obj.update({
                    "is_connect": True,
                    "connect_date": now,
                    "description": 'Turn On',
                    "duration": req['otp_type'] if req.get('otp_type') and req['otp_type'] != '' else 'never'
                })
            user_obj.is_using_otp = True
            return ERR.get_no_error()
        return ERR.get_error(500, additional_message='Invalid OTP')

    def turn_off_otp_user_api(self, req, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        ## NEED TEST

        now = datetime.now()
        otp_objs = self.env['tt.otp'].search([
            ('machine_id.code', '=', req['machine_code']),
            ('otp', '=', req['otp']),
            ('otp', '=', req['otp']),
            ('disconnect_date','=', False),
            ('purpose_type','=', 'turn_off'),
            ('is_connect','=', False),
            ('create_date', '>', datetime.now() - timedelta(minutes=user_obj.ho_id.otp_expired_time))
        ])
        if otp_objs:
            notes = ['Turn Off:']
            ### TURN OFF ALL OTP
            other_otp_objs = self.env['tt.otp'].search([
                ('user_id.id', '=', user_obj.id),
                ('purpose_type', '=', 'turn_on'),
                ('is_connect', '=', True),
                ('is_disconnect', '=', False)
            ])
            for other_otp_obj in other_otp_objs:
                other_otp_obj.update({
                    'is_disconnect': True,
                    'disconnect_date': now
                })
                notes.append("%s %s" % (other_otp_obj.machine_id.code, other_otp_obj.otp))
            for otp_obj in otp_objs:
                otp_obj.update({
                    "is_connect": True,
                    "is_disconnect": True,
                    "connect_date": now,
                    "disconnect_date": now,
                    'description': "\n".join(notes)
                })
            user_obj.is_using_otp = False
            return ERR.get_no_error()
        return ERR.get_error(500, additional_message='Invalid OTP')

    def turn_off_machine_otp_user_api(self, req, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        ## NEED TEST
        now = datetime.now()
        otp_objs = self.env['tt.otp'].search([
            ('machine_id.code', '=', req['machine_code']),
            ('otp', '=', req['otp']),
            ('purpose_type','=', 'turn_off_this_machine'),
            ('is_connect','=', False),
            ('create_date', '>', now - timedelta(minutes=user_obj.ho_id.otp_expired_time))
        ])
        if otp_objs:
            notes = ['Turn this machine:']
            other_otp_objs = self.env['tt.otp'].search([
                ('machine_id.code', '=', req['machine_code']),
                ('purpose_type','=','turn_on'),
                ('is_connect', '=', True),
                ('is_disconnect', '=', False)
            ])
            for other_otp_obj in other_otp_objs:
                other_otp_obj.update({
                    "is_disconnect": True,
                    "disconnect_date": now
                })
                notes.append("%s %s" % (other_otp_obj.machine_id.code, other_otp_obj.otp))
            for otp_obj in otp_objs:
                otp_obj.update({
                    "is_connect": True,
                    "is_disconnect": True,
                    "connect_date": now,
                    "disconnect_date": now,
                    'description': "\n".join(notes)
                })
            return ERR.get_no_error()
        return ERR.get_error(500, additional_message='Invalid OTP')

    def turn_off_other_machine_otp_user_api(self, req, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        ## NEED TEST
        now = datetime.now()
        otp_objs = self.env['tt.otp'].search([
            ('machine_id.code', '=', req['machine_code']),
            ('otp', '=', req['otp']),
            ('purpose_type','=','turn_off_other_machine'),
            ('is_connect','=', False),
            ('create_date', '>', now - timedelta(minutes=user_obj.ho_id.otp_expired_time))
        ])
        if otp_objs:
            notes = ['Turn Off:']
            ### TURN OFF OTHER MACHINE
            other_otp_objs = self.env['tt.otp'].search([
                ('machine_id.code', '!=', req['machine_code']),
                ('is_connect', '=', True),
                ('is_disconnect', '=', False),
                ('purpose_type','=', 'turn_on')
            ])
            for other_otp_obj in other_otp_objs:
                other_otp_obj.update({
                    "is_disconnect": True,
                    "disconnect_date": now
                })
                notes.append("%s %s" % (other_otp_obj.machine_id.code, other_otp_obj.otp))

            for otp_obj in otp_objs:
                otp_obj.update({
                    "is_connect": True,
                    "is_disconnect": True,
                    "connect_date": now,
                    "disconnect_date": now,
                    'description': "\n".join(notes)
                })
            return ERR.get_no_error()
        return ERR.get_error(500, additional_message='Invalid OTP')


class TtAgent(models.Model):
    _inherit = 'tt.agent'
    otp_expired_time = fields.Integer('OTP Expired Time in Minutes', default=5)

class TtMachine(models.Model):
    _name = "tt.machine"
    _order = "id desc"
    _description = "Machine ID"
    _rec_name = 'code'

    code = fields.Char('Machine Code')
    platform = fields.Char('Platform')
    browser = fields.Char('Browser')
    timezone = fields.Char('Timezone')
    user_id = fields.Many2one('res.users')
    otp_ids = fields.One2many('tt.otp', 'machine_id', 'OTP', readonly=True)

    def create_or_get_machine_api(self, req):
        machine_obj = self.sudo().search([('code','=', req['machine_code'])])
        if machine_obj:
            data_update = {}
            if machine_obj.platform == '' and req.get('platform'):
                data_update.update({
                    "platform": req['platform']
                })
            if machine_obj.browser == '' and req.get('browser'):
                data_update.update({
                    "browser": req['browser']
                })
            if machine_obj.timezone == '' and req.get('timezone'):
                data_update.update({
                    "timezone": req['timezone']
                })
            return machine_obj
        else:
            return self.create({
                "code": req['machine_code'],
                "platform": req.get('platform', ''),
                "browser": req.get('browser', ''),
                "timezone": req.get('timezone', ''),
            })

class TtOtp(models.Model):

    _name = "tt.otp"
    _order = "id desc"
    _description = "OTP User"

    machine_id = fields.Many2one('tt.machine', 'Machine ID', ondelete='cascade')
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    agent_id = fields.Many2one('tt.agent', 'Agent', related='user_id.agent_id', readonly=True)
    otp = fields.Char('OTP')
    is_connect = fields.Boolean('Connect', default=False)
    is_disconnect = fields.Boolean('Disconnect', default=False)
    platform = fields.Char('Platform', related='machine_id.platform', readonly=True)
    browser = fields.Char('Browser', related='machine_id.browser', readonly=True)
    timezone = fields.Char('Timezone', related='machine_id.timezone', readonly=True)
    # turn_off_date = fields.Datetime('Turn Off Date', readonly=True)
    purpose_type = fields.Selection([
        ('turn_on', 'Turn On'), ('turn_off', 'Turn Off All OTP'), ('turn_off_other_machine', 'Turn Off Other Machine'),
        ('turn_off_this_machine', 'Turn Off This Machine'), ('change_pin', 'Change Pin')], string='Purpose Type', default='turn_on')

    duration = fields.Selection([
        ('always', 'Always'), ('1', '1 Days'), ('3', '3 Days'),
        ('7', '7 Days'), ('never', 'First time only')], string='Duration', default='never')


    disconnect_date = fields.Datetime('Disconnect Time', readonly=True)
    connect_date = fields.Datetime('Connect Time', readonly=True)

    # otp_connect_date = fields.Datetime('Turn Off Date', readonly=True)
    #
    # need_otp_type = fields.Selection([
    #     ('always', 'Always'), ('1', '1 Days'), ('3', '3 Days'),
    #     ('7', '7 Days'), ('never', 'First time only')], string='OTP Type')
    description = fields.Text('Description', default='')
    active = fields.Boolean('Active', default=True)


    def update_otp_type_api(self, req):
        self.need_otp_type = req['need_otp_type']
        return ERR.get_no_error()

    def create_otp(self, user_id, purpose_type, machine_obj):
        return self.create({
            "machine_id": machine_obj.id,
            "otp": self.generate_otp(),
            "user_id": user_id,
            "purpose_type": purpose_type
        })

    def generate_otp(self):
        digits = "0123456789"
        OTP = ""

        # length of password can be changed
        # by changing value in range
        for i in range(6):
            OTP += digits[math.floor(random.random() * 10)]

        return OTP

    def get_company_name(self):
        company_obj = self.env['res.company'].search([],limit=1)
        return company_obj.name

    def get_other_machine(self):
        other_machine = ''
        otp_objs = self.search([('user_id', '=', self.user_id.id), ('is_connect','=', True), ('machine_id.id','!=',self.machine_id.id)])
        for otp_obj in otp_objs:
            if other_machine:
                other_machine += ', '
            other_machine += otp_obj.machine_id.code
        return other_machine

    def get_expired_time(self):
        return (self.create_date + timedelta(minutes=self.user_id.ho_id.otp_expired_time)).strftime("%a, %d %b %Y %H:%M:%S")

    @api.multi
    def send_email_otp(self):
        template = self.env.ref('tt_base.template_mail_otp', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)

    @api.multi
    def send_email_turn_off_otp(self):
        template = self.env.ref('tt_base.template_mail_turn_off_otp', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)

    @api.multi
    def send_email_change_pin(self):
        template = self.env.ref('tt_base.template_mail_change_pin', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)

    @api.multi
    def send_email_turn_off_machine(self):
        template = self.env.ref('tt_base.template_mail_turn_off_machine_otp', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)

    @api.multi
    def send_email_turn_off_other_machine(self):
        template = self.env.ref('tt_base.template_mail_turn_off_other_machine_otp', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)

