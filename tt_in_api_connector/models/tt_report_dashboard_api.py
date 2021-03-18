from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback


class TtReportDashboardApiCon(models.Model):
    _name = 'tt.report.dashboard.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.report.dashboard'

    def action_call(self,table_obj,action,data,context):
        if action == 'get_report_json':
            res = table_obj.get_report_json_api(data,context)
        elif action == 'get_report_xls':
            res = table_obj.get_report_xls_api(data,context)
        elif action == 'get_vendor_balance':
            res = self.env['tt.provider'].get_vendor_balance_api(context)
        else:
            raise RequestException(999)

        return res


