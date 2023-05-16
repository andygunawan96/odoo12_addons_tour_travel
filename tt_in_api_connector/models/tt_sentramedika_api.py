from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtSwabExpressApiCon(models.Model):
    _name = 'tt.sentramedika.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.sentramedika'

    def action_call(self,table_obj,action,data,context):
        if action == 'get_config':
            res = self.env['tt.provider.sentramedika'].get_carriers_api()
        elif action == 'get_availability':
            res = self.env['tt.timeslot.sentramedika'].get_available_timeslot_api(data, context)
        elif action == 'get_price':
            res = table_obj.get_price_sentramedika_api(data,context)
        elif action == 'create_booking':
            res = table_obj.create_booking_sentramedika_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_sentramedika_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_sentramedika_api(data,context)
        elif action == 'confirm_order':
            res = table_obj.confirm_order_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_sentramedika_api(data,context)
        elif action == 'get_transaction_by_analyst':
            res = table_obj.get_transaction_by_analyst_api(data,context)
        elif action == 'update_data_verif':
            res = table_obj.update_data_verif(data, context)
        else:
            raise RequestException(999)
        return res

    def send_confirm_order_notification(self,document_number,confirm_name,timeslot,address, ho_id):
        request = {
            'code': 9938,
            'message': '{} has been Confirmed by {}\n{}\n{}'.format(document_number,confirm_name,timeslot,address),
            "title": 'CONFIRMED <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code', ho_id=ho_id)

    def send_cancel_order_notification(self,document_number,confirm_name,timeslot,address,ho_id):
        request = {
            'code': 9940,
            'message': '{} has been cancel by {}\n{}\n{}'.format(document_number,confirm_name,timeslot,address),
            "title": 'CANCEL <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code',ho_id=ho_id)