from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback


class TtTourApiCon(models.Model):
    _name = 'tt.tour.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.tour'

    def action_call(self,table_obj,action,data,context):

        if action == 'update_passenger':
            res = table_obj.update_passenger_api(data,context)
        elif action == 'get_booking':
            res = table_obj.get_booking_api(data,context)
        elif action == 'commit_booking':
            res = table_obj.commit_booking_api(data,context)
        elif action == 'issued_booking':
            res = table_obj.issued_booking_api(data,context)
        elif action == 'update_booking':
            res = table_obj.update_booking_api(data,context)
        else:
            raise RequestException(999)

        return res


class TtMasterTourApiCon(models.Model):
    _name = 'tt.master.tour.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.master.tour'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_config':
            res = table_obj.get_config_by_api()
        elif action == 'search':
            res = table_obj.search_tour_api(data,context)
        elif action == 'get_details':
            res = table_obj.get_tour_details_api(data,context)
        elif action == 'get_pricing':
            res = table_obj.get_pricing_api(data)
        elif action == 'get_autocomplete':
            res = table_obj.get_autocomplete_api(data,context)
        else:
            raise RequestException(999)

        return res


