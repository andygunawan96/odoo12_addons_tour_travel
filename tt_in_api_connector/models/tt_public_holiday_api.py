from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtAirlineApiCon(models.Model):
    _name = 'tt.public.holiday.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.public.holiday'

    def action_call(self, table_obj, action, data, context):

        if action == 'get_public_holiday':
            res = table_obj.get_public_holiday_api(data, context)
        else:
            raise RequestException(999)
        return res
