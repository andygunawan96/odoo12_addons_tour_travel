from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtReservationPPOBApiCon(models.Model):
    _name = 'tt.reservation.ppob.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.ppob'

    def action_call(self,table_obj,action,data,context):

        if action == 'search_inquiry':
            res = table_obj.search_inquiry_api(data,context)
        elif action == 'get_inquiry':
            res = table_obj.get_inquiry_api(data,context)
        elif action == 'create_inquiry':
            res = table_obj.create_inquiry_api(data,context)
        elif action == 'update_inquiry':
            res = table_obj.update_inquiry_api(data,context)
        elif action == 'issued_payment_ppob':
            res = table_obj.issued_payment_api(data,context)
        elif action == 'update_inquiry_status':
            res = table_obj.update_inquiry_status_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_ppob_api(data, context)
        else:
            raise RequestException(999)
        return res

    def get_balance(self,provider):
        res = self.send_request_to_gateway('%s/booking/ppob' % (self.url),{'provider': provider},'get_balance')
        if res['error_code'] != 0:
            raise Exception(res)
        return res

