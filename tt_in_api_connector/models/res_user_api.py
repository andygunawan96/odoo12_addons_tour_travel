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
        else:
            raise RequestException(999)
        return res

