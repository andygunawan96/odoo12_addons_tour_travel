from odoo import api, fields, models, _
import math
import random
from datetime import datetime, timedelta
from ...tools.ERR import RequestException
from ...tools import ERR
class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    is_using_otp = fields.Boolean('Use OTP', default=False)
    machine_ids = fields.One2many('tt.machine', 'user_id', 'Machine IDs', readonly=True)

    def check_need_otp_user_api(self, req):
        is_machine_connect = False
        ## NEED TEST
        if req.get('machine_code'):
            otp_objs = self.env['tt.otp'].search([
                ('machine_id.code','=', req['machine_code']),
                ('user_id.id','=', self.id),
                ('is_connect','=', True)
            ])
        else:
            otp_objs = []
        for otp_obj in otp_objs:
            if otp_obj.need_otp_type:
                # if otp_obj.need_otp_type == 'always': ## ALWAYS SKIP KARENA SELALU MINTA OTP
                #     is_machine_connect = False
                #     otp_obj.active = False
                if otp_obj.need_otp_type == 'never':
                    is_machine_connect = True
                elif len(otp_obj.need_otp_type) == 1: ## DAYS
                    if otp_obj.create_date + timedelta(datetime=int(otp_obj.need_otp_type)) > datetime.now():
                        is_machine_connect = True
                    else:
                        otp_obj.active = False
            else:
                is_machine_connect = True

        if self.is_using_otp and not is_machine_connect:
            self.check_otp_user_api(req)
            # expired_date = self.check_otp_user_api(req)
            # return expired_date

    def create_or_get_otp_user_api(self, req):
        ho_obj = self.ho_id
        ## NEED TEST

        machine_objs = self.env['tt.machine'].search([
            ('code', '=', req['machine_code']),
            ('user_id.id', '=', self.id)
        ])

        if not machine_objs:
            machine_objs = [self.env['tt.machine'].create_or_get_machine_api(req)]
            self.machine_ids = [(4, machine_objs[0].id)]

        for machine_obj in machine_objs:
            otp_objs = machine_obj.otp_ids.filtered(lambda x:
                        x.create_date > datetime.now() - timedelta(minutes=ho_obj.otp_expired_time) and
                        x.turn_off_date == False and x.is_connect == False)
            is_need_send_email = False
            if otp_objs:
                if req.get('is_resend_otp'):
                    is_need_send_email = True
                    for otp_obj in otp_objs:
                        otp_obj.active = False
                    otp_objs = [self.env['tt.otp'].create_otp_api(req, self.id)]
                else:
                    return otp_objs[0]
            else:
                is_need_send_email = True
                otp_objs = [self.env['tt.otp'].create_otp_api(req, self.id)]
            if is_need_send_email:
                if req.get('turn_off_otp'):
                    otp_objs[0].send_email_turn_off_otp()
                elif req.get('turn_off_machine_id') and req.get('is_turn_off_other_machine'):
                    otp_objs[0].send_email_turn_off_other_machine()
                elif req.get('turn_off_machine_id'):
                    otp_objs[0].send_email_turn_off_machine()
                else:
                    otp_objs[0].send_email_otp()
            return otp_objs[0]


        # otp_objs = self.env['tt.otp'].search([
        #     ('machine_id.code', '=', req['machine_code']),
        #     ('user_id.id', '=', self.id),
        #     ('is_connect','=', False),
        #     ('create_date', '>', datetime.now() - timedelta(minutes=agent_obj.otp_expired_time)),
        #     ('turn_off_date','=', False)
        # ])
        # if not otp_objs or req.get('is_resend_otp'):
        #     ## close active otp
        #     for otp_obj in otp_objs:
        #         otp_obj.active = False
        #
        #     otp_objs = [self.env['tt.otp'].create_otp_api(req)]
        #     self.otp_ids = [(4, otp_objs[0].id)]
        #     if req.get('turn_off_otp'):
        #         otp_objs[0].send_email_turn_off_otp()
        #     elif req.get('turn_off_machine_id') and req.get('is_turn_off_other_machine'):
        #         otp_objs[0].send_email_turn_off_other_machine()
        #     elif req.get('turn_off_machine_id'):
        #         otp_objs[0].send_email_turn_off_machine()
        #     else:
        #         otp_objs[0].send_email_otp()
        #     ## KIRIM EMAIL
        # return otp_objs[0]

    def check_otp_user_api(self, req):
        ho_obj = self.ho_id
        if req.get('otp'):
            ## NEED TEST
            machine_objs = self.env['tt.machine'].search([
                ('code', '=', req['machine_code']),
                ('user_id.id', '=', self.id)
            ])

            if machine_objs:
                for machine_obj in machine_objs:
                    otp_objs = machine_obj.otp_ids.filtered(lambda x: x.otp == req['otp'] and x.create_date > datetime.now() - timedelta(minutes=ho_obj.otp_expired_time))
                    if otp_objs:
                        for otp_obj in otp_objs:
                            otp_obj.is_connect = True
                            otp_obj.need_otp_type = req['otp_type']
                        return True
            raise RequestException(1041)


            # otp_objs = self.env['tt.otp'].search([
            #     ('code','=', req['machine_code']),
            #     ('otp','=', req['otp']),
            #     ('user_id.id','=', self.id),
            #     ('create_date','>', datetime.now() - timedelta(minutes=ho_obj.otp_expired_time))
            # ])
            # if otp_objs:
            #     for otp_obj in otp_objs:
            #         otp_obj.is_connect = True
            #     return False
            # else:
            #     return True
        else:
            ## NO OTP CODE CREATE
            otp_obj = self.create_or_get_otp_user_api(req)
            raise RequestException(1040, additional_message=(otp_obj.create_date + timedelta(minutes=ho_obj.otp_expired_time)).strftime('%Y-%m-%d %H:%M:%S'))
            # return (otp_obj.create_date + timedelta(minutes=ho_obj.otp_expired_time)).strftime('%Y-%m-%d %H:%M:%S')

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

        # otp_objs = self.env['tt.otp'].search([
        #     ('code', '=', req['machine_code']),
        #     ('otp', '=', req['otp']),
        #     ('user_id.id', '=', user_obj.id),
        #     ('create_date', '>', datetime.now() - timedelta(minutes=user_obj.ho_id.otp_expired_time))
        # ])

        ## NEED TEST
        machine_objs = self.env['tt.machine'].search([
            ('code', '=', req['machine_code']),
            ('user_id.id', '=', user_obj.id)
        ])

        if machine_objs:
            for machine_obj in machine_objs:
                otp_objs = machine_obj.otp_ids.filtered(lambda x: x.otp == req['otp'] and x.create_date > datetime.now() - timedelta(minutes=user_obj.ho_id.otp_expired_time))
                if otp_objs:
                    for otp_obj in otp_objs:
                        otp_obj.is_connect = True
                        otp_obj.need_otp_type = req.get('otp_type', 'never')
                    user_obj.is_using_otp = True
                    return ERR.get_no_error()
                return ERR.get_error(500, additional_message='Invalid OTP')
        else:
            return ERR.get_error(500, additional_message='Invalid OTP')

        # if otp_objs:
        #     for otp_obj in otp_objs:
        #         otp_obj.is_connect = True
        #     user_obj.is_using_otp = True
        #     return ERR.get_no_error()
        # else:
        #     return ERR.get_error(500, additional_message='Invalid OTP')

    def turn_off_otp_user_api(self, req, context):
        turn_off_date = datetime.now()
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        ## NEED TEST

        machine_objs = self.env['tt.machine'].search([
            ('code', '=', req['machine_code']),
            ('user_id.id', '=', user_obj.id)
        ])

        if machine_objs:
            for machine_obj in machine_objs:
                otp_objs = machine_obj.otp_ids.filtered(
                    lambda x: x.otp == req['otp'] and x.create_date > datetime.now() - timedelta(
                        minutes=user_obj.ho_id.otp_expired_time))
                if otp_objs:
                    otp_objs = machine_obj.otp_ids.filtered(lambda x: x.is_connect)
                    for otp_obj in otp_objs:
                        otp_obj.is_connect = False
                        otp_obj.turn_off_date = turn_off_date

                    ### TURN OFF OTHER MACHINE
                    other_machine_objs = self.env['tt.machine'].search([
                        ('code', '!=', req['machine_code']),
                        ('user_id.id', '=', user_obj.id)
                    ])
                    for other_machine_obj in other_machine_objs:
                        other_otp_objs = other_machine_obj.otp_ids.filtered(lambda x:x.is_connect)
                        for other_otp_obj in other_otp_objs:
                            other_otp_obj.is_connect = False
                            other_otp_obj.turn_off_date = turn_off_date
                    user_obj.is_using_otp = False
                    return ERR.get_no_error()
                return ERR.get_error(500, additional_message='Invalid OTP')
        else:
            ##ASUMSI TIDAK PERNAH KESINI
            return ERR.get_error(500, additional_message='Invalid OTP')


        # otp_objs = self.env['tt.otp'].search([
        #     ('code', '=', req['machine_code']),
        #     ('otp', '=', req['otp']),
        #     ('user_id.id', '=', user_obj.id),
        #     ('create_date', '>', datetime.now() - timedelta(minutes=user_obj.ho_id.otp_expired_time))
        # ])
        # if otp_objs:
        #     turn_off_date = datetime.now()
        #     for otp_obj in otp_objs:
        #         otp_obj.is_connect = False
        #         otp_obj.turn_off_date = turn_off_date
        #     otp_objs = self.env['tt.otp'].search([
        #         ('is_connect', '=', True),
        #         ('user_id.id', '=', user_obj.id)
        #     ])
        #     for otp_obj in otp_objs:
        #         otp_obj.is_connect = False
        #         otp_obj.turn_off_date = turn_off_date
        #
        #     user_obj.is_using_otp = False
        #     return ERR.get_no_error()
        # else:
        #     return ERR.get_error(500, additional_message='Invalid OTP')


    def turn_off_machine_otp_user_api(self, req, context):
        turn_off_date = datetime.now()
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        ## NEED TEST

        machine_objs = self.env['tt.machine'].search([
            ('code', '=', req['machine_code']),
            ('user_id.id', '=', user_obj.id)
        ])

        if machine_objs:
            for machine_obj in machine_objs:
                otp_objs = machine_obj.otp_ids.filtered(
                    lambda x: x.otp == req['otp'] and x.create_date > datetime.now() - timedelta(
                        minutes=user_obj.ho_id.otp_expired_time))
                if otp_objs:
                    otp_objs = machine_obj.otp_ids.filtered(lambda x: x.is_connect)
                    for otp_obj in otp_objs:
                        otp_obj.is_connect = False
                        otp_obj.turn_off_date = turn_off_date

                    return ERR.get_no_error()
                return ERR.get_error(500, additional_message='Invalid OTP')
        else:
            ##ASUMSI TIDAK PERNAH KESINI
            return ERR.get_error(500, additional_message='Invalid OTP')


        # otp_objs = self.env['tt.otp'].search([
        #     ('code', '=', req['machine_code']),
        #     ('otp', '=', req['otp']),
        #     ('user_id.id', '=', user_obj.id),
        #     ('create_date', '>', datetime.now() - timedelta(minutes=user_obj.ho_id.otp_expired_time))
        # ])
        # if otp_objs:
        #     otp_objs = self.env['tt.otp'].search([
        #         ('is_connect', '=', True),
        #         ('code', '=', req['machine_code']),
        #         ('user_id.id', '=', user_obj.id)
        #     ])
        #     for otp_obj in otp_objs:
        #         otp_obj.is_connect = False
        #         otp_obj.turn_off_date = datetime.now()
        #
        #     return ERR.get_no_error()
        # else:
        #     return ERR.get_error(500, additional_message='Invalid OTP')

    def turn_off_other_machine_otp_user_api(self, req, context):
        turn_off_date = datetime.now()
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        ## NEED TEST

        machine_objs = self.env['tt.machine'].search([
            ('code', '=', req['machine_code']),
            ('user_id.id', '=', user_obj.id)
        ])

        if machine_objs:
            for machine_obj in machine_objs:
                otp_objs = machine_obj.otp_ids.filtered(
                    lambda x: x.otp == req['otp'] and x.create_date > datetime.now() - timedelta(
                        minutes=user_obj.ho_id.otp_expired_time))
                if otp_objs:

                    ### TURN OFF OTHER MACHINE
                    other_machine_objs = self.env['tt.machine'].search([
                        ('code', '!=', req['machine_code']),
                        ('user_id.id', '=', user_obj.id)
                    ])
                    for other_machine_obj in other_machine_objs:
                        other_otp_objs = other_machine_obj.otp_ids.filtered(lambda x: x.is_connect)
                        for other_otp_obj in other_otp_objs:
                            other_otp_obj.is_connect = False
                            other_otp_obj.turn_off_date = turn_off_date

                    return ERR.get_no_error()
                return ERR.get_error(500, additional_message='Invalid OTP')
        else:
            ##ASUMSI TIDAK PERNAH KESINI
            return ERR.get_error(500, additional_message='Invalid OTP')

        # otp_objs = self.env['tt.otp'].search([
        #     ('code', '=', req['machine_code']),
        #     ('otp', '=', req['otp']),
        #     ('user_id.id', '=', user_obj.id),
        #     ('create_date', '>', datetime.now() - timedelta(minutes=user_obj.ho_id.otp_expired_time))
        # ])
        # if otp_objs:
        #     otp_objs = self.env['tt.otp'].search([
        #         ('is_connect', '=', True),
        #         ('code', '!=', req['machine_code']),
        #         ('user_id.id', '=', user_obj.id)
        #     ])
        #     for otp_obj in otp_objs:
        #         otp_obj.is_connect = False
        #         otp_obj.turn_off_date = datetime.now()
        #
        #     return ERR.get_no_error()
        # else:
        #     return ERR.get_error(500, additional_message='Invalid OTP')

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
        machine_obj = self.search([('code','=', req['machine_code'])])
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
                "platform": req['platform'],
                "browser": req['browser'],
                "timezone": req.get('timezone', ''),
            })

class TtOtp(models.Model):

    _name = "tt.otp"
    _order = "id desc"
    _description = "OTP User"

    machine_id = fields.Many2one('tt.machine', 'Machine ID')
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    agent_id = fields.Many2one('tt.agent', 'Agent', related='user_id.agent_id', readonly=True)
    otp = fields.Char('OTP')
    is_connect = fields.Boolean('Connect', default=False)
    is_turn_off_request = fields.Boolean('Turn Off Request', default=False)
    platform = fields.Char('Platform', related='machine_id.platform', readonly=True)
    browser = fields.Char('Browser', related='machine_id.browser', readonly=True)
    timezone = fields.Char('Timezone', related='machine_id.timezone', readonly=True)
    turn_off_date = fields.Datetime('Turn Off Date', readonly=True)
    need_otp_type = fields.Selection([
        ('always', 'Always'), ('1', '1 Days'), ('3', '3 Days'),
        ('7', '7 Days'), ('never', 'First time only')], string='OTP Type')
    active = fields.Boolean('Active', default=True)


    def update_otp_type_api(self, req):
        self.need_otp_type = req['need_otp_type']
        return ERR.get_no_error()

    def create_otp_api(self, req, user_id):
        machine_obj = self.env['tt.machine'].create_or_get_machine_api(req)

        return self.create({
            "machine_id": machine_obj.id,
            "otp": self.generate_otp(),
            "user_id": user_id,
            "is_turn_off_request": req.get('turn_off_otp', False),
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
    def send_email_turn_off_machine(self):
        template = self.env.ref('tt_base.template_mail_turn_off_machine_otp', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)

    @api.multi
    def send_email_turn_off_other_machine(self):
        template = self.env.ref('tt_base.template_mail_turn_off_other_machine_otp', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)

