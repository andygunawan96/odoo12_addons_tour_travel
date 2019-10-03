from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback


class TtMasterActivityApiCon(models.Model):
    _name = 'tt.master.tour.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.master.tour'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_config':
            res = table_obj.get_config_by_api()
        else:
            raise RequestException(999)

        return res


