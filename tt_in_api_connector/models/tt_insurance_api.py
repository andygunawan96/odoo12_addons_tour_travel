from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtPhcApiCon(models.Model):
    _name = 'tt.insurance.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.insurance'

    def action_call(self,table_obj,action,data,context):
        if action == 'get_config':
            res = self.env['tt.destinations'].get_all_city_for_insurance()
        elif action == 'create_booking':
            res = table_obj.create_booking_insurance_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_phc_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_phc_api(data,context)
        else:
            raise RequestException(999)
        return res

    def send_confirm_order_notification(self,document_number,confirm_name,timeslot,address):
        request = {
            'code': 9917,
            'message': '{} has been Confirmed by {}\n{}\n{}'.format(document_number,confirm_name,timeslot,address),
            "title": 'CONFIRMED <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code')

    def sync_status_with_phc(self, req):
        request = {
            'ticket_number': req.get('ticket_number'),
            'carrier_code': req.get('carrier_code'),
            'provider': req.get('provider')
        }
        action = 'sync_status_with_phc'
        return self.send_request_to_gateway('%s/booking/phc/private' % (self.url),
                                            request,
                                            action,
                                            timeout=180)