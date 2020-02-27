from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtTopUpQuotaApiCon(models.Model):
    _name = 'tt.top.up.quota.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.pnr.quota'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_top_up_quota':
            res = self.env['tt.agent'].get_available_pnr_price_list_api(data, context)
        elif action == 'buy_quota_pnr':
            res = table_obj.create_pnr_quota_api(data, context)
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
                                            ,'notification_api')