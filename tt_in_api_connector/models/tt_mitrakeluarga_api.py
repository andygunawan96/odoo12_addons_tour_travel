from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtSwabExpressApiCon(models.Model):
    _name = 'tt.mitrakeluarga.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.mitrakeluarga'

    def action_call(self,table_obj,action,data,context):
        if action == 'get_config':
            res = self.env['tt.provider.mitrakeluarga'].get_carriers_api()
        elif action == 'get_availability':
            res = self.env['tt.timeslot.mitrakeluarga'].get_available_timeslot_api(data, context)
        elif action == 'get_price':
            res = table_obj.get_price_mitrakeluarga_api(data,context)
        elif action == 'create_booking':
            res = table_obj.create_booking_mitrakeluarga_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_mitrakeluarga_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_mitrakeluarga_api(data,context)
        elif action == 'confirm_order':
            res = table_obj.confirm_order_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_mitrakeluarga_api(data,context)
        elif action == 'get_transaction_by_analyst':
            res = table_obj.get_transaction_by_analyst_api(data,context)
        elif action == 'update_data_verif':
            res = table_obj.update_data_verif(data, context)
        else:
            raise RequestException(999)
        return res

    def send_confirm_order_notification(self,document_number,confirm_name,timeslot,address):
        request = {
            'code': 9934,
            'message': '{} has been Confirmed by {}\n{}\n{}'.format(document_number,confirm_name,timeslot,address),
            "title": 'CONFIRMED <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code')
