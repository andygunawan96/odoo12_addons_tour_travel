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
        elif action == 'refund_request_set_to_confirm_api':
            res = self.env['tt.refund'].set_to_confirm_api(data, context)
        elif action == 'refund_request_validate_api':
            res = self.env['tt.refund'].validate_refund_from_button_api(data, context)
        elif action == 'validate_refund_api':
            res = self.env['tt.refund'].validate_refund_api(data, context)
        elif action == 'finalize_refund_from_button_api':
            res = self.env['tt.refund'].finalize_refund_from_button_api(data, context)
        elif action == 'action_approve_api':
            res = self.env['tt.refund'].action_approve_api(data, context)
        else:
            raise RequestException(999)

        return res

    def send_refund_request(self, request, ho_id):
        return self.send_request_to_gateway('%s/booking/%s' % (self.url, request['res_model'].split('.')[2]), request, 'refund_request_api', timeout=300, ho_id=ho_id)