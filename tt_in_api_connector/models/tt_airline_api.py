from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtAirlineApiCon(models.Model):
    _name = 'tt.airline.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.airline'

    def action_call(self,table_obj,action,data,context):

        if action == 'create_booking':
            res = table_obj.create_booking_airline_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_airline_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_airline_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_airline_api(data,context)
        elif action == 'update_cost_service_charges':
            res = table_obj.update_cost_service_charge_airline_api(data,context)
        elif action == 'create_reschedule':
            res = table_obj.create_reschedule_airline_api(data,context)
        elif action == 'update_reschedule':
            res = table_obj.update_reschedule_airline_api(data,context)
        elif action == 'get_reschedule':
            res = table_obj.get_reschedule_airline_api(data,context)
        elif action == 'create_refund':
            res = table_obj.create_refund_airline_api(data,context)
        elif action == 'update_refund':
            res = table_obj.update_refund_airline_api(data,context)
        elif action == 'get_refund':
            res = table_obj.get_refund_airline_api(data,context)
        elif action == 'split_booking':
            res = table_obj.split_reservation_airline_api(data,context)
        elif action == 'get_provider_booking_from_vendor':
            res = self.env['tt.get.booking.from.vendor'].get_provider_booking_from_vendor_api()
        elif action == 'get_booking_frontend_check_pnr':
            res = self.env['tt.get.booking.from.vendor'].pnr_validator_api(data, context)
        elif action == 'save_booking_from_vendor':
            res = self.env['tt.get.booking.from.vendor.review'].save_booking_api(data, context)
        elif action == 'process_update_booking':
            res = table_obj.process_update_booking_airline_api(data,context)
        elif action == 'create_update_booking_payment':
            res = table_obj.create_update_booking_payment_api(data,context)
        elif action == 'get_booking_number':
            res = table_obj.get_booking_number_airline_api(data, context)
        elif action == 'update_pax_identity_booking':
            res = table_obj.update_pax_identity_airline_api(data, context)
        elif action == 'update_pax_name_booking':
            res = table_obj.update_pax_name_airline_api(data, context)
        else:
            raise RequestException(999)

        return res

    def get_balance(self,provider):
        return self.send_request_to_gateway('%s/account/airline' % (self.url),{'provider': provider},'get_vendor_balance',timeout=60)

    def send_force_issued_not_enough_balance_notification(self,order_number,context):
        request = {
            'code': 9901,
            'message': 'Agent/Customer doesn\'t have enough balance, but issued on vendor.\n\nCo User Name : {}\nCo User Agent : {}\n\mOrder Number : {}'.format(context['co_user_name'],context['co_agent_name'],order_number),
            "title": 'URGENT NOT ENOUGH BALANCE'
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request,
                                            'notification_code')

    def send_duplicate_segment_notification(self,messages):
        request = {
            'code': 9909,
            'message': messages,
            "title": 'DUPLICATE SEGMENT FOUND'
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code')

    def send_get_booking_from_vendor(self, req):
        request = {
            'proxy_co_uid': req.get('user_id',False),
            'pnr': req.get('pnr'),
            'provider': req.get('provider'),
            'is_retrieved': req.get('is_retrieved',False),
            'pricing_date': req.get('pricing_date',False)
        }
        return self.send_request_to_gateway('%s/booking/airline/private' % (self.url),
                                            request,
                                            'retrieve_booking',
                                            timeout=120)

    # June 2, 2021 - SAM
    def send_reprice_booking_vendor(self, req):
        request = {
            'proxy_co_uid': req.get('user_id',False),
            'pnr': req.get('pnr', ''),
            'pnr2': req.get('pnr2', ''),
            'reference': req.get('reference', ''),
            'provider': req.get('provider'),
            'is_retrieved': req.get('is_retrieved',False),
            'pricing_date': req.get('pricing_date',False),
            'context': req.get('context', {}),
        }
        return self.send_request_to_gateway('%s/booking/airline/private' % (self.url),
                                            request,
                                            'reprice_booking',
                                            timeout=120)
    # END

    # March 28, 2022 - SAM
    def send_void_booking_vendor(self, req):
        request = {
            'proxy_co_uid': req.get('user_id',False),
            'pnr': req.get('pnr', ''),
            'pnr2': req.get('pnr2', ''),
            'reference': req.get('reference', ''),
            'provider': req.get('provider'),
            'is_retrieved': req.get('is_retrieved',False),
            'pricing_date': req.get('pricing_date',False),
            'context': req.get('context', {}),
        }
        return self.send_request_to_gateway('%s/booking/airline/private' % (self.url),
                                            request,
                                            'void_booking',
                                            timeout=120)
    # END

    def send_sync_refund_status(self, req):
        request = {
            'proxy_co_uid': req.get('user_id',False),
            'pnr': req.get('pnr', ''),
            'pnr2': req.get('pnr2', ''),
            'provider': req.get('provider', ''),
        }
        return self.send_request_to_gateway('%s/booking/airline/private' % (self.url),
                                            request,
                                            'refund_status',
                                            timeout=120)

    def send_get_booking_for_sync(self, req):
        request = {
            'order_number': req.get('order_number'),
            'proxy_co_uid': req.get('user_id', False),
            'force_sync': True,
        }
        return self.send_request_to_gateway('%s/booking/airline' % (self.url),
                                            request,
                                            'get_booking',
                                            timeout=180)
    def send_get_original_ticket(self, req):
        request = req
        request.update({
            'proxy_co_uid': req.get('user_id', False)
        })
        return self.send_request_to_gateway('%s/booking/airline/private' % (self.url),
                                            request,
                                            'get_original_ticket',
                                            timeout=180)

    def cancel_booking(self, req):
        request = {
            'order_number': req.get('order_number'),
        }
        return self.send_request_to_gateway('%s/booking/airline' % (self.url),
                                            request,
                                            'cancel',
                                            timeout=180)

    # December 29, 2021 - SAM
    def send_vendor_ticket_email(self, req):
        request = {
            'proxy_co_uid': req.get('user_id',False),
            'pnr': req.get('pnr', ''),
            'pnr2': req.get('pnr2', ''),
            'provider': req.get('provider'),
        }
        return self.send_request_to_gateway('%s/booking/airline/private' % (self.url),
                                            request,
                                            'send_vendor_ticket_itinerary',
                                            timeout=120)
    # END