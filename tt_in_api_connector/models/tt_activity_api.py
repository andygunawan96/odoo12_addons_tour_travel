from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback

class TtActivityApiCon(models.Model):
    _name = 'tt.activity.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.activity'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_vouchers':
            res = table_obj.get_vouchers_by_api2(data,context)
        elif action == 'create_booking':
            res = table_obj.create_booking_activity_api(data,context)
        elif action == 'update_booking':
            res = table_obj.update_booking_by_api(data,context)
        elif action == 'update_booking2':
            order_id = data['order_id']
            book_info = data['book_info']
            res = table_obj.update_booking_by_api2(order_id, book_info)
        elif action == 'action_failed':
            order_id = data['order_id']
            error_msg = data['error_msg']
            res = table_obj.action_failed(order_id, error_msg)
        elif action == 'get_booking':
            order_number = data['order_number']
            res = table_obj.get_booking(order_number)
        elif action == 'get_booking_for_vendor_by_api':
            res = table_obj.get_booking_for_vendor_by_api(data, context)
        elif action == 'get_booking_by_api':
            temp_res = data['res']
            temp_req = data['req']
            res = table_obj.get_booking_by_api(temp_res, temp_req, context)
        elif action == 'confirm_booking_webhook':
            res = table_obj.confirm_booking_webhook(data)
        else:
            raise RequestException(999)

        return res

    def resend_voucher(self, data):
        return self._send_request('%s/booking/activity' % (self.url), data, 'resend_voucher')

    def update_booking(self, data):
        return self._send_request('%s/booking/activity' % (self.url), data, 'update_booking')

    def get_booking(self, data):
        req_post = {
            'order_number': data.get('order_number', ''),
            'order_id': data.get('order_id', ''),
            'provider': data.get('provider', ''),
            'uuid': data.get('uuid', ''),
            'pnr': data.get('pnr', ''),
        }
        return self._send_request('%s/booking/activity' % (self.url), req_post, 'get_booking_provider')

    def get_pricing(self, data):
        req_post = {
            'product_type_uuid': data.get('product_type_uuid', ''),
            'date_start': data.get('date_start', ''),
            'date_end': data.get('date_end', ''),
            'provider': data.get('provider', ''),
        }
        return self._send_request('%s/booking/activity' % (self.url), req_post, 'get_pricing_provider')

    def get_vouchers(self, data):
        return self._send_request('%s/booking/activity' % (self.url), data, 'get_vouchers_provider')


class TtMasterActivityApiCon(models.Model):
    _name = 'tt.master.activity.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.master.activity'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_config':
            res = table_obj.get_config_by_api()
        elif action == 'search':
            res = table_obj.search_by_api(data,context)
        elif action == 'get_details':
            res = table_obj.get_details_by_api(data,context)
        elif action == 'reprice_currency':
            res = table_obj.reprice_currency(data,context)
        elif action == 'product_update_webhook':
            res = table_obj.product_update_webhook(data,context)
        elif action == 'product_type_update_webhook':
            res = table_obj.product_type_update_webhook(data,context)
        elif action == 'product_type_inactive_webhook':
            res = table_obj.product_type_inactive_webhook(data,context)
        else:
            raise RequestException(999)

        return res

    def get_config(self, data):
        return self._send_request('%s/booking/activity' % (self.url), data, 'get_config_provider', timeout=600)

    def search_provider(self, data):
        return self._send_request('%s/booking/activity' % (self.url), data, 'search_provider', timeout=900)

    def get_details(self, data):
        return self._send_request('%s/booking/activity' % (self.url), data, 'get_details_provider', timeout=600)

    def send_product_analytics(self, data):
        return self._send_request('%s/booking/activity' % (self.url), data, 'send_product_analytics')

    def get_countries(self, data):
        return self._send_request('%s/booking/activity' % (self.url), data, 'get_countries', timeout=600)

