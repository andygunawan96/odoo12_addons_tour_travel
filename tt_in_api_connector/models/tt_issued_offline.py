from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtOfflineApiCon(models.Model):
    _name = 'tt.offline.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.offline'

    def action_call(self, table_obj, action, data, context):

        if action == 'get_config':
            res = table_obj.get_config_api()
        elif action == 'create_booking_reservation_offline_api':
            res = table_obj.create_booking_reservation_offline_api(data, context)
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