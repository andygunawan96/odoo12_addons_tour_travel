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
        elif action == 'create_reservation_issued_request_api':
            res = table_obj.create_reservation_issued_request_api(data,context)
        elif action == 'create_booker_api':
            booker_obj = table_obj.create_booker_api(data,context)
            res = {'booker_seq_id': booker_obj.seq_id}
        elif action == 'create_customer_api':
            list_customer_obj = table_obj.create_customer_api(data,context)
            res = {'passengers_seq_id': {}}
            for idx, customer_obj in enumerate(list_customer_obj):
                if data[idx]['pax_type'] not in res['passengers_seq_id']:
                    res['passengers_seq_id'][data[idx]['pax_type']] = []
                res['passengers_seq_id'][data[idx]['pax_type']].append(customer_obj.seq_id)
        else:
            raise RequestException(999)

        return res
