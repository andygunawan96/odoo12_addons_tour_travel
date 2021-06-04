from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtTrainApiCon(models.Model):
    _name = 'tt.periksain.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.periksain'

    def action_call(self,table_obj,action,data,context):

        if action == 'create_booking':
            res = table_obj.create_booking_periksain_api(data,context)
        elif action == 'update_pnr_provider':
            res = table_obj.update_pnr_provider_periksain_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_periksain_api(data,context)
        elif action == 'payment':
            res = table_obj.payment_periksain_api(data,context)
        else:
            raise RequestException(999)
        return res