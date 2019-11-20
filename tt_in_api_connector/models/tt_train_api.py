from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtAirlineApiCon(models.Model):
    _name = 'tt.train.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.train'

    def action_call(self,table_obj,action,data,context):

        if action == 'create_booking':
            res = table_obj.create_booking_train_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_train_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_train_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_train_api(data,context)
        elif action == 'update_cost_service_charges':
            res = table_obj.update_cost_service_charge_airline_api(data,context)
        elif action == 'update_seat':
            res = table_obj.update_seat_train_api(data,context)
        else:
            raise RequestException(999)

        return res

    # def get_balance(self,provider):
    #     return self._send_request('%s/account/airline' % (self.url),{'provider': provider},'get_vendor_balance')

