from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtPhcApiCon(models.Model):
    _name = 'tt.phc.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.phc'

    def action_call(self,table_obj,action,data,context):
        if action == 'get_config':
            res = self.env['tt.provider.phc'].get_carriers_api()
        elif action == 'get_availability':
            res = self.env['tt.timeslot.phc'].get_available_timeslot_api(data, context)
        elif action == 'get_price':
            res = table_obj.get_price_phc_api(data,context)
        elif action == 'create_booking':
            res = table_obj.create_booking_phc_api(data,context)
        elif action == 'edit_passenger_verify_api':
            res = table_obj.edit_passenger_verify_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_phc_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_phc_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_phc_api(data,context)
        elif action == 'get_transaction_by_analyst':
            res = table_obj.get_transaction_by_analyst_api(data,context)
        elif action == 'update_data_verif':
            res = table_obj.update_data_verif(data, context)
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

    def send_cancel_order_notification(self,document_number,confirm_name,timeslot,address):
        request = {
            'code': 9919,
            'message': '{} has been cancel by {}\n{}\n{}'.format(document_number,confirm_name,timeslot,address),
            "title": 'CANCEL <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code')