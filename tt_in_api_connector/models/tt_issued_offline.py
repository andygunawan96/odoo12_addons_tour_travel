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