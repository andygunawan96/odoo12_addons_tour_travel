from odoo import api,models,fields
from ...tools.ERR import RequestException


class TtAgentApiCon(models.Model):
    _name = 'tt.agent.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.agent'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_reconcile_data':
            res = table_obj.get_reconcile_data_api(data,context)
        else:
            raise RequestException(999)

        return res

