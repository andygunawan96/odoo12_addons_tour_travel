from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtTopUpApiCon(models.Model):
    _name = 'tt.top.up.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.top.up'

    def action_call(self,table_obj,action,data,context):

        if action == 'create_top_up':
            res = table_obj.create_top_up_api(data,context)
        elif action == 'request_top_up':
            res = table_obj.request_top_up_api(data,context)
        elif action == 'get_top_up':
            res = table_obj.get_top_up_api(data,context)
        elif action == 'get_va_number':
            res = self.env['payment.acquirer'].get_va_number(data,context)
        elif action == 'get_va_bank':
            res = self.env['payment.acquirer'].get_va_bank(data,context)
        elif action == 'cancel_top_up':
            res = table_obj.cancel_top_up_api(data,context)
        elif action == 'get_top_up_amount':
            res = self.env['tt.top.up.amount'].get_top_up_amount_api()
        else:
            raise RequestException(999)
        return res

    def send_approve_notification(self,document_number,approve_uid,amount,agent_name):
        request = {
            'code': 9907,
            'message': 'Top Up from {} has been Approved by {} Rp {:,}'.format(agent_name,approve_uid,amount),
            "title": 'APPROVED <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code')