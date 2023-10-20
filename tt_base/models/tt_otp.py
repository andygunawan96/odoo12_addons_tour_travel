from odoo import api, fields, models, _
import math
import random
from datetime import datetime, timedelta
from ...tools.ERR import RequestException
from ...tools import ERR
class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    is_use_otp = fields.Boolean('Use OTP', default=False)
    otp_ids = fields.One2many('tt.otp', 'user_id', 'OTPs')

    def check_need_otp_user_api(self, req):
        if not self.is_use_otp or self.otp_ids.filtered(lambda x: x.machine_id.code == req['machine_code'] and x.is_connect):
            return False
        else:
            expired_date = self.check_otp_user_api(req)
            return expired_date

    def create_or_get_otp_user_api(self, req):
        agent_obj = self.ho_id
        otp_objs = self.env['tt.otp'].search([
            ('machine_id.code', '=', req['machine_code']),
            ('user_id.id', '=', self.id),
            ('create_date', '>', datetime.now() - timedelta(minutes=agent_obj.otp_expired_time))
        ])
        if not otp_objs or req.get('is_resend_otp'):
            ## close active otp
            for otp_obj in otp_objs:
                otp_obj.active = False

            otp_objs = [self.env['tt.otp'].create_otp_api(req)]
            self.otp_ids = [(4, otp_objs[0].id)]
            ## KIRIM EMAIL
        return otp_objs[0]

    def check_otp_user_api(self, req):
        agent_obj = self.ho_id
        if req.get('otp'):
            otp_objs = self.env['tt.otp'].search([
                ('machine_id.code','=', req['machine_code']),
                ('otp','=', req['otp']),
                ('user_id.id','=', self.id),
                ('create_date','>', datetime.now() - timedelta(minutes=agent_obj.otp_expired_time))
            ])
            if otp_objs:
                for otp_obj in otp_objs:
                    otp_obj.is_connect = True
                return False
            else:
                return True
        else:
            ## NO OTP CODE CREATE
            otp_obj = self.create_or_get_otp_user_api(req)
            return (otp_obj.create_date + timedelta(minutes=agent_obj.otp_expired_time)).strftime('%Y-%m-%d %H:%M:%S')

    def set_otp_user_api(self, req, context):
        user_obj = self.browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)
        ## ASUMSI SEBELUM SET OTP DARI FRONTEND, OTP TIDAK AKTIF ##
        otp_obj = user_obj.create_or_get_otp_user_api(req)
        return ERR.get_no_error((otp_obj.create_date + timedelta(minutes=user_obj.ho_id.otp_expired_time)).strftime('%Y-%m-%d %H:%M:%S'))

    def activation_otp_user_api(self, req, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        otp_objs = self.env['tt.otp'].search([
            ('machine_id.code', '=', req['machine_code']),
            ('otp', '=', req['otp']),
            ('user_id.id', '=', user_obj.id),
            ('create_date', '>', datetime.now() - timedelta(minutes=user_obj.ho_id.otp_expired_time))
        ])
        if otp_objs:
            for otp_obj in otp_objs:
                otp_obj.is_connect = True
            user_obj.is_use_otp = True
            return ERR.get_no_error()
        else:
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

    def create_or_get_machine_api(self, machine_code):
        machine_obj = self.search([('code','=', machine_code)])
        if machine_obj:
            return machine_obj
        else:
            return self.create({
                "code": machine_code
            })

class TtOtp(models.Model):

    _name = "tt.otp"
    _order = "id desc"
    _description = "OTP User"

    machine_id = fields.Many2one('tt.machine', 'Machine ID')
    user_id = fields.Many2one('res.users')
    otp = fields.Char('OTP')
    is_connect = fields.Boolean('Connect', default=False)
    platform = fields.Char('Platform')
    browser = fields.Char('Browser')
    active = fields.Boolean('Active', default=True)

    def create_otp_api(self, req):
        machine_obj = self.env['tt.machine'].create_or_get_machine_api(req['machine_code'])

        return self.create({
            "machine_id": machine_obj.id,
            "otp": self.generate_otp(),
            "platform": req['platform'],
            "browser": req['browser']
        })

    def generate_otp(self):
        digits = "0123456789"
        OTP = ""

        # length of password can be changed
        # by changing value in range
        for i in range(6):
            OTP += digits[math.floor(random.random() * 10)]

        return OTP



