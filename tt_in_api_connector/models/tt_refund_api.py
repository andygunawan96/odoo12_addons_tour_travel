from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtRefundApiCon(models.Model):
    _name = 'tt.refund.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.refund.wizard'

    def action_call(self, table_obj, action, data, context):

        if action == 'refund_request_api':
            res = self.env['tt.refund.wizard'].refund_api(data, context)
        elif action == 'refund_request_confirm_api':
            res = self.env['tt.refund'].refund_confirm_api(data, context)
        elif action == 'refund_request_sent_to_agent':
            res = self.env['tt.refund'].refund_request_sent_to_agent_api(data, context)
        else:
            raise RequestException(999)

        return res

    def send_refund_request(self, request):
        return self.send_request_to_gateway('%s/booking/%s' % (self.url, request['res_model'].split('.')[2]), request, 'refund_request_api', timeout=300)