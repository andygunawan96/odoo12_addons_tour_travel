from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtReservationRequestApiCon(models.Model):
    _name = 'tt.reservation.request.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.request'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_issued_request_list_api':
            res = table_obj.get_issued_request_list_api(data,context)
        elif action == 'get_issued_request_api':
            res = table_obj.get_issued_request_api(data,context)
        elif action == 'approve_issued_request_api':
            res = table_obj.approve_issued_request_api(data,context)
        elif action == 'reject_issued_request_api':
            res = table_obj.reject_issued_request_api(data,context)
        elif action == 'cancel_issued_request_api':
            res = table_obj.cancel_issued_request_api(data,context)
        else:
            raise RequestException(999)

        return res
