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
        elif action == 'file_upload':
            res = table_obj.file_upload_api(data,context)
        elif action == 'create_booking':
            res = table_obj.create_booking_activity_api(data,context)
        elif action == 'issued_booking':
            res = table_obj.issued_booking_by_api(data,context)
        elif action == 'update_booking':
            res = table_obj.update_booking_by_api(data,context)
        elif action == 'update_booking2':
            res = table_obj.update_booking_by_api2(data)
        elif action == 'cancel_booking':
            res = table_obj.cancel_booking_by_api(data,context)
        elif action == 'action_failed':
            res = table_obj.action_failed(data)
        elif action == 'get_booking':
            order_number = data['order_number']
            ho_id = table_obj.search([('name','=', order_number)], limit=1).agent_id.ho_id.id
            res = table_obj.get_booking(order_number, ho_id)
        elif action == 'get_booking_for_vendor_by_api':
            res = table_obj.get_booking_for_vendor_by_api(data, context)
        elif action == 'get_booking_by_api':
            temp_res = data['res']
            temp_req = data['req']
            res = table_obj.get_booking_by_api(temp_res, temp_req, context)
        elif action == 'confirm_booking_webhook':
            res = table_obj.confirm_booking_webhook(data)
        elif action == 'payment':
            res = table_obj.payment_activity_api(data,context)
        else:
            raise RequestException(999)

        return res

    def get_balance(self, provider_ho_data_obj,provider, ho_id):
        return self.send_request_to_gateway('%s/account/activity' % (self.url),{'provider': provider},'get_vendor_balance', ho_id=ho_id)

    def resend_voucher(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'resend_voucher', ho_id=data.get('ho_id'))

    def issued_booking_vendor(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'issued_booking_vendor', ho_id=data.get('ho_id'))

    def get_booking(self, data, ho_id):
        req_post = {
            'order_number': data.get('order_number', ''),
            'order_id': data.get('order_id', ''),
            'provider': data.get('provider', ''),
            'uuid': data.get('uuid', ''),
            'pnr': data.get('pnr', ''),
        }
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), req_post, 'get_booking_provider', ho_id=data.get('ho_id'))

    def get_pricing(self, data):
        req_post = {
            'product_type_uuid': data.get('product_type_uuid', ''),
            'date_start': data.get('date_start', ''),
            'date_end': data.get('date_end', ''),
            'provider': data.get('provider', ''),
        }
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), req_post, 'get_pricing_provider')

    def get_vouchers(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'get_vouchers_provider', ho_id=data.get('ho_id'))

    def file_upload(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'file_upload_provider')


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
        elif action == 'get_autocomplete':
            res = table_obj.get_autocomplete_api(data,context)
        elif action == 'product_update_webhook':
            res = table_obj.product_update_webhook(data,context)
        elif action == 'product_type_new_webhook':
            res = table_obj.product_type_new_webhook(data,context)
        elif action == 'product_type_update_webhook':
            res = table_obj.product_type_update_webhook(data,context)
        elif action == 'product_type_inactive_webhook':
            res = table_obj.product_type_inactive_webhook(data,context)
        elif action == 'product_sync_webhook_nosend':
            res = table_obj.product_sync_webhook_nosend(data,context)
        else:
            raise RequestException(999)

        return res

    def get_config(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'get_config_provider', timeout=600)

    def search_provider(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'search_provider', timeout=1800)

    def get_details(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'get_details_provider', timeout=600)

    def get_details_bulk(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'get_details_bulk_provider', timeout=1800)

    def send_product_analytics(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'send_product_analytics')

    def get_countries(self, data):
        return self.send_request_to_gateway('%s/booking/activity' % (self.url), data, 'get_countries', timeout=600)
