from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtPeriksainApiCon(models.Model):
    _name = 'tt.periksain.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.periksain'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_availability':
            res = self.env['tt.timeslot.periksain'].get_available_timeslot_api(context)
        elif action == 'get_price':
            res = table_obj.get_price_periksain_api(data,context)
        elif action == 'create_booking':
            res = table_obj.create_booking_periksain_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_periksain_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_periksain_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_periksain_api(data,context)
        elif action == 'get_transaction_by_analyst':
            res = table_obj.get_transaction_by_analyst_api(data,context)
        elif action == 'confirm_order':
            res = table_obj.confirm_order(data, context)
        elif action == 'cancel_order':
            res = table_obj.cancel_order(data, context)
        elif action == 'update_result_url':
            res = table_obj.update_result_url(data, context)
        else:
            raise RequestException(999)
        return res

    def send_confirm_order_notification(self,document_number,confirm_name,timeslot,address, ho_id):
        request = {
            'code': 9913,
            'message': '{} has been Confirmed by {}\n{}\n{}'.format(document_number,confirm_name,timeslot,address),
            "title": 'CONFIRMED <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code', ho_id=ho_id)

    def get_config_cron(self):
        data = {
            "provider": 'periksain'
        }
        return self.send_request_to_gateway('%s/booking/periksain' % (self.url), data, 'get_config_cron',timeout=60)

    def send_cancel_order_notification(self,document_number,confirm_name,timeslot,address,ho_id):
        request = {
            'code': 9915,
            'message': '{} has been cancel by {}\n{}\n{}'.format(document_number,confirm_name,timeslot,address),
            "title": 'CANCEL <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code',ho_id=ho_id)