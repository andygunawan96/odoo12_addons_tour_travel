from odoo import api, fields, models, _
from odoo.exceptions import UserError
import math
import random
from datetime import datetime, timedelta
from ...tools.ERR import RequestException
from ...tools import ERR
import pytz
import logging, traceback

_logger = logging.getLogger(__name__)

class TtPinLog(models.Model):
    _name = "tt.pin.log"
    _order = "id desc"
    _description = "Pin Log"
    _rec_name = 'purpose_type'

    user_id = fields.Many2one('res.users', 'User', readonly=True)
    purpose_type = fields.Selection([
        ('set', 'Set Pin'), ('change', 'Change Pin'), ('change_by_otp', 'Change By OTP'), ('turn_off', 'Turn Off Pin'),
        ('wrong', 'Incorrect Pin'), ('correct', 'Correct Pin')], string='Purpose Type',
        default='turn_on')
    is_bypass_check = fields.Boolean('Bypass check', default=False)
    datetime_bypass_check = fields.Datetime('DateTime Bypass', readonly=True)

    def create_pin_log(self, user_obj, purpose_type):
        self.sudo().create({
            "user_id": user_obj.id,
            "purpose_type": purpose_type,
        })
        self.env.cr.commit()
        self.check_ban_pin_log(user_obj)

    def check_ban_pin_log(self, user_obj):
        pin_log_objs = self.sudo().search([('user_id','=', user_obj.id), ('is_bypass_check','=', False)], limit=user_obj.ho_id.max_wrong_pin)
        wrong_pin_counter = 0
        for pin_log_obj in pin_log_objs:
            if pin_log_obj.purpose_type == 'wrong':
                wrong_pin_counter += 1
        if wrong_pin_counter >= user_obj.ho_id.max_wrong_pin:
            self.env['tt.ban.user'].sudo().ban_user(user_obj.id, 1576800, {})
            try:
                self.env['tt.api.con'].send_ban_user_error_notification(user_obj.name, 'wrong pin %s times' % user_obj.ho_id.max_wrong_pin, user_obj.ho_id.id)
            except Exception as e:
                _logger.info(str(e), traceback.format_exc())
            raise RequestException(4030)

    def ban_user_bypass_pin_log(self, user_id):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = "UPDATE tt_pin_log SET is_bypass_check=True, datetime_bypass_check='%s' where user_id=%s" % (now, user_id)
        self.env.cr.execute(query)