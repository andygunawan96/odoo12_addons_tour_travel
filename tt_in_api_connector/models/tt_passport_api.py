from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtVisaApiCon(models.Model):
    _name = 'tt.passport.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.passport'

    def action_call(self, table_obj, action, data, context):

        if action == 'get_config_api':
            res = self.env['tt.reservation.passport.pricelist'].get_config_api()
        elif action == 'get_inventory_api':
            res = self.env['tt.reservation.passport.pricelist'].get_inventory_api()
        elif action == 'get_inventory_detail_api':
            res = self.env['tt.reservation.passport.pricelist'].get_product_detail_api(data)
        elif action == 'search_api':
            res = self.env['tt.reservation.passport.pricelist'].search_api(data)
        elif action == 'availability_api':
            res = self.env['tt.reservation.passport.pricelist'].availability_api(data)
        elif action == 'create_booking_passport_api':
            res = table_obj.create_booking_passport_api(data, context)
        elif action == 'state_booking_passport_api':
            res = table_obj.state_booking_passport_api(data, context)
        elif action == 'change_pnr_api':
            res = table_obj.change_pnr_api(data, context)
        elif action == 'get_booking_passport_api':
            res = table_obj.get_booking_passport_api(data, context)
        elif action == 'payment':
            res = self.env['tt.reservation.passport'].payment_visa_api(data,context)
        elif action == 'issued_booking_visa_api':
            res = self.env['tt.reservation.passport'].action_issued_visa_api(data,context)
        else:
            raise RequestException(999)

        return res

    def get_balance(self, provider_ho_data_obj, provider, ho_id):
        return self.send_request_to_gateway('%s/account/passport' % (self.url),{'provider': provider},'get_vendor_balance', ho_id=ho_id)

    def get_product_vendor(self, data):
        return self.send_request_to_gateway('%s/booking/passport' % (self.url), data, 'get_product_provider', timeout=600)

    def get_product_detail_vendor(self, data):
        return self.send_request_to_gateway('%s/booking/passport' % (self.url), data, 'get_product_detail_provider', timeout=600)