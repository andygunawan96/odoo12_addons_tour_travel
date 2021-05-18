from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtReservationApiCon(models.Model):
    _name = 'tt.reservation.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_booking_b2c_api':
            res = table_obj.get_booking_b2c_api(data,context)
        elif action == 'cancel_payment_method_api':
            res = table_obj.cancel_payment(data,context)
        else:
            raise RequestException(999)

        return res
