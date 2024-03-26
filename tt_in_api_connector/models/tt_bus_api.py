from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtBusApiCon(models.Model):
    _name = 'tt.bus.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.master.bus.station'

    def action_call(self,table_obj,action,data,context):
        if action == 'get_config':
            res = self.env['tt.master.bus.station'].get_config_api()
        elif action == 'create_booking':
            res = self.env['tt.reservation.bus'].create_booking_bus_api(data,context)
        elif action == 'get_booking':
            res = self.env['tt.reservation.bus'].get_booking_bus_api(data,context)
        elif action == 'update_pnr_provider':
            res = self.env['tt.reservation.bus'].update_pnr_provider_bus_api(data, context)
        elif action == 'payment':
            res = self.env['tt.reservation.bus'].payment_bus_api(data,context)
        else:
            raise RequestException(999)
        return res

    def sync_data(self, req, ho_id):
        request = {
            "provider": "ta_bus"
        }
        action = 'sync_data'
        return self.send_request_to_gateway('%s/booking/bus/private' % (self.url),
                                            request,
                                            action,
                                            timeout=180, ho_id=ho_id)
    def sync_get_data_journey(self, req, ho_id):
        request = {
            "provider": "ta_bus",
            "id": req['id']
        }
        action = 'sync_get_data_journey'
        return self.send_request_to_gateway('%s/booking/bus/private' % (self.url),
                                            request,
                                            action,
                                            timeout=180, ho_id=ho_id)
