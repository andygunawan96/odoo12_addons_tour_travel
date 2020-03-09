from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtMonitorData(models.Model):
    _name = 'tt.monitor.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.api.monitor'

    def action_call(self, table_obj, action, data, context):
        if action == 'create_monitor_data':
            res = table_obj.create_monitor_api(data,context)
        else:
            raise RequestException(999)
        return res