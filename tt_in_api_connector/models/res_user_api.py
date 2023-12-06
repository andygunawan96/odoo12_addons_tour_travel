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

    def send_inactive_dormant_users_notification(self,messages_dict, ho_id):
        total_length = len(messages_dict)-1## 1 of the key is for ctr so minus 1
        for idx,values in messages_dict.items():
            if idx == 'ctr':## skip ctr
                continue
            request = {
                'code': 9909,
                'message': values,
                "title": 'Dormant Users Archived\n(%s/%s)' % (idx+1,total_length)
            }
            self.send_request_to_gateway('%s/notification' % (self.url),
                                                request
                                                ,'notification_code', ho_id=ho_id)
