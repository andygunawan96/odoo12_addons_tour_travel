from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtHotelApiCon(models.Model):
    _name = 'tt.hotel.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.hotel'

    def action_call(self,table_obj,action,data,context):
        if action == 'create_booking':
            res = table_obj.create_booking_hotel_api(data,context)
        elif action == 'action_done_hotel':
            res = table_obj.action_done_hotel_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_hotel_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_hotel_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_hotel_api(data,context)
        elif action == 'update_cost_service_charges':
            res = table_obj.update_cost_service_charge_hotel_api(data,context)
        elif action == 'create_refund':
            res = table_obj.create_refund_hotel_api(data,context)
        else:
            raise RequestException(999)
        return res

    def get_balance(self, provider_ho_data_obj, provider, ho_id):
        return self.send_request_to_gateway('%s/account/hotel' % (self.url), {'provider': provider}, 'get_vendor_balance', ho_id=ho_id)

    def check_booking_status(self, data, ho_id):
        return self.send_request_to_gateway('%s/booking/hotel' % (self.url), data, 'check_booking_status', ho_id=ho_id)

    def cancel_booking(self, data, ho_id):
        return self.send_request_to_gateway('%s/booking/hotel' % (self.url), data, 'cancel_booking')
