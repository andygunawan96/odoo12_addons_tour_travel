from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtOfflineApiCon(models.Model):
    _name = 'tt.groupbooking.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.groupbooking'

    def action_call(self, table_obj, action, data, context):

        if action == 'get_config':
            res = table_obj.get_config_api()
        elif action == 'create_booking_reservation_groupbooking_api':
            res = table_obj.create_booking_reservation_groupbooking_api(data, context)
        elif action == 'get_booking_reservation_groupbooking_api':
            res = table_obj.get_booking_reservation_groupbooking_api(data, context)
        elif action == 'get_all_booking_state_booked_api':
            res = table_obj.get_all_booking_state_booked_api(context)
        elif action == 'update_passenger_api':
            res = table_obj.update_passenger_api(data, context)
        elif action == 'pick_ticket_api':
            res = table_obj.pick_ticket_api(data, context)
        elif action == 'update_booker_api':
            res = table_obj.update_booker_api(data, context)
        elif action == 'update_contact_api':
            res = table_obj.update_contact_api(data, context)
        elif action == 'check_data_can_sent_api':
            res = table_obj.check_data_can_sent_api(data, context)
        elif action == 'change_state_to_booked_api':
            res = table_obj.change_state_to_booked_api(data, context)
        elif action == 'change_state_back_to_confirm_api':
            res = table_obj.change_state_back_to_confirm_api(data, context)
        elif action == 'payment':
            res = table_obj.payment_groupbooking_api(data, context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_groupbooking_api(data,context)
        else:
            raise RequestException(999)

        return res

    def send_approve_notification(self,document_number,approve_uid,amount):
        request = {
            'code': 9906,
            'message': 'Issued Offline by {} Rp {:,}'.format(approve_uid,amount),
            "title": 'ISSUED <b>%s</b>' % (document_number)
        }
        return self.send_request_to_gateway('%s/notification' % (self.url),
                                            request
                                            ,'notification_code')