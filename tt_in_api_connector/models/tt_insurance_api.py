from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtInsuranceApiCon(models.Model):
    _name = 'tt.insurance.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.insurance'

    def action_call(self,table_obj,action,data,context):
        if action == 'create_booking':
            res = table_obj.create_booking_insurance_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_insurance_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_insurance_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_insurance_api(data,context)
        else:
            raise RequestException(999)
        return res

    def send_confirm_order_notification(self,document_number,confirm_name,timeslot,address, ho_id):
        request = {
            'code': 9917,
            'message': '{} has been Confirmed by {}\n{}\n{}'.format(document_number,confirm_name,timeslot,address),
            "title": 'CONFIRMED <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code', ho_id=ho_id)

    def send_get_original_ticket(self, req):
        request = req
        request.update({
            'proxy_co_uid': req.get('user_id', False)
        })
        return self.send_request_to_gateway('%s/booking/insurance/private' % (self.url),
                                            request,
                                            'get_original_ticket',
                                            timeout=180, ho_id=req['ho_id'])