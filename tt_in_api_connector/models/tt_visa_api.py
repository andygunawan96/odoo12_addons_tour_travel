from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtOfflineApiCon(models.Model):
    _name = 'tt.visa.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.visa'

    def action_call(self, table_obj, action, data, context):

        if action == 'get_config_api':
            res = self.env['tt.reservation.visa.pricelist'].get_config_api()
        elif action == 'search_api':
            res = self.env['tt.reservation.visa.pricelist'].search_api(data)
        elif action == 'create_booking_visa_api':
            res = table_obj.create_booking_visa_api(data, context)
        elif action == 'get_booking_visa_api':
            res = table_obj.get_booking_visa_api(data, context)
        else:
            raise RequestException(999)

        return res