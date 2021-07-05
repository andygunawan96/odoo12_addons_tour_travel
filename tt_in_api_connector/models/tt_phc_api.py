from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtTrainApiCon(models.Model):
    _name = 'tt.phc.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.phc'

    def action_call(self,table_obj,action,data,context):
        if action == 'get_config':
            res = self.env['tt.provider.phc'].get_carriers_api()
        elif action == 'get_availability':
            res = self.env['tt.timeslot.phc'].get_available_timeslot_api(data, context)
        elif action == 'get_price':
            res = table_obj.get_price_phc_api(data,context)
        elif action == 'create_booking':
            res = table_obj.create_booking_phc_api(data,context)
        elif action == 'edit_passenger_verify_api':
            res = table_obj.edit_passenger_verify_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_phc_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_phc_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_phc_api(data,context)
        elif action == 'get_transaction_by_analyst':
            res = table_obj.get_transaction_by_analyst_api(data,context)
        else:
            raise RequestException(999)
        return res