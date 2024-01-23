from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtPPOBApiCon(models.Model):
    _name = 'tt.ppob.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.ppob'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_config':
            res = table_obj.get_config_api(data,context)
        elif action == 'search_inquiry':
            res = table_obj.search_inquiry_api(data,context)
        elif action == 'get_inquiry':
            res = table_obj.get_inquiry_api(data,context)
        elif action == 'create_inquiry':
            res = table_obj.create_inquiry_api(data,context)
        elif action == 'update_inquiry':
            res = table_obj.update_inquiry_api(data,context)
        elif action == 'issued_payment_ppob':
            res = table_obj.issued_payment_api(data,context)
        elif action == 'get_provider_booking_ppob':
            res = table_obj.get_provider_api(data,context)
        elif action == 'update_pay_amount_ppob':
            res = table_obj.update_pay_amount_api(data, context)
        elif action == 'update_inquiry_status':
            res = table_obj.update_inquiry_status_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_ppob_api(data,context)
        elif action == 'resync_status':
            res = table_obj.action_resync_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_ppob_api(data, context)
        else:
            raise RequestException(999)
        return res

    def get_balance(self, provider_ho_data_obj, provider, ho_id):
        return self.send_request_to_gateway('%s/account/ppob' % (self.url), {'provider': provider,'product_code': 524}, 'get_vendor_balance', ho_id=ho_id)

