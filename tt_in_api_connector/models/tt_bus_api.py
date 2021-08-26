from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtTrainApiCon(models.Model):
    _name = 'tt.bus.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.master.bus.station'

    def action_call(self,table_obj,action,data,context):
        if action == 'get_config':
            res = self.env['tt.master.bus.station'].get_config_api()
        elif action == 'get_availability':
            res = self.env['tt.timeslot.phc'].get_available_timeslot_api(data, context)
        elif action == 'get_price':
            res = table_obj.get_price_phc_api(data,context)
        elif action == 'create_booking':
            res = self.env['tt.reservation.bus'].create_booking_bus_api(data,context)
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
        elif action == 'update_data_verif':
            res = table_obj.update_data_verif(data, context)
        else:
            raise RequestException(999)
        return res

    def sync_data(self, req):
        request = {
            "provider": "traveloka_bus"
        }
        action = 'sync_data'
        return self.send_request_to_gateway('%s/booking/bus/private' % (self.url),
                                            request,
                                            action,
                                            timeout=180)
    def sync_get_data_journey(self, req):
        request = {
            "provider": "traveloka_bus",
            "id": req['id']
        }
        action = 'sync_get_data_journey'
        return self.send_request_to_gateway('%s/booking/bus/private' % (self.url),
                                            request,
                                            action,
                                            timeout=180)