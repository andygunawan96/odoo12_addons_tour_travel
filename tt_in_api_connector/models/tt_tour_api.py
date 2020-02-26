from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback


class TtTourApiCon(models.Model):
    _name = 'tt.tour.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.tour'

    def action_call(self,table_obj,action,data,context):

        if action == 'update_passenger':
            res = table_obj.update_passenger_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_api(data,context)
        elif action == 'get_booking_for_vendor_by_api':
            res = table_obj.get_booking_for_vendor_by_api(data,context)
        elif action == 'commit_booking':
            res = table_obj.commit_booking_api(data,context)
        elif action == 'issued_booking':
            res = table_obj.issued_booking_api(data,context)
        elif action == 'update_booking':
            res = table_obj.update_booking_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_tour_api(data,context)
        else:
            raise RequestException(999)

        return res

    def send_tour_payment_expired_notification(self,data,context):
        request = {
            'code': 9901,
            'message': 'Tour Payment Expired: {}\n\nOrder Number : {}\nTour : {}\nDue Date : {}'.format(data['url'], data['tour_name'],data['order_number'],data['due_date']),
            "title": 'TOUR PAYMENT EXPIRED'
        }
        return self.send_request_to_gateway('%s/notification' % (self.url), request, 'notification_api')


class TtMasterTourApiCon(models.Model):
    _name = 'tt.master.tour.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.master.tour'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_config':
            res = table_obj.get_config_by_api()
        elif action == 'search':
            res = table_obj.search_tour_api(data,context)
        elif action == 'get_details':
            res = table_obj.get_tour_details_api(data,context)
        elif action == 'get_payment_rules':
            res = table_obj.get_payment_rules_api(data,context)
        elif action == 'get_pricing':
            res = table_obj.get_pricing_api(data)
        elif action == 'get_autocomplete':
            res = table_obj.get_autocomplete_api(data,context)
        else:
            raise RequestException(999)

        return res

    def send_tour_request_notification(self,data,context):
        request = {
            'code': 9908,
            'message': 'New Tour Request: {}\n\nCo User Name : {}\nCo User Agent : {}\n\nRequest Number : {}'.format(data['url'], context['co_user_name'],context['co_agent_name'],data['req_number']),
            "title": 'TOUR PACKAGE REQUEST'
        }
        return self.send_request_to_gateway('%s/notification' % (self.url), request, 'notification_api')


