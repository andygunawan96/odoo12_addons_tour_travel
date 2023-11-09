from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException

class TtBankApiCon(models.Model):
    _name = 'res.users.api.con'
    _inherit = 'tt.api.con'

    table_name = 'res.users'

    def action_call(self,table_obj,action,data,context):

        if action == 'set_otp_user_api':
            res = table_obj.set_otp_user_api(data,context)
        elif action == 'activation_otp_user_api':
            res = table_obj.activation_otp_user_api(data,context)
        elif action == 'turn_off_otp_user_api':
            res = table_obj.turn_off_otp_user_api(data,context)
        elif action == 'turn_off_machine_otp_user_api':
            res = table_obj.turn_off_machine_otp_user_api(data,context)
        elif action == 'turn_off_other_machine_otp_user_api':
            res = table_obj.turn_off_other_machine_otp_user_api(data,context)
        elif action == 'delete_user_api':
            res = table_obj.delete_user_api(context)
        elif action == 'turn_on_pin_api':
            res = table_obj.turn_on_pin_api(data, context)
        elif action == 'turn_off_pin_api':
            res = table_obj.turn_off_pin_api(data, context)
        elif action == 'change_pin_api':
            res = table_obj.change_pin_api(data, context)
        elif action == 'change_pin_otp_api':
            res = table_obj.change_pin_otp_api(data, context)
        else:
            raise RequestException(999)
        return res

