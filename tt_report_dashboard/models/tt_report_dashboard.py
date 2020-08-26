from odoo import models, fields, api, _
from ...tools import variables,util,ERR
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtReportDashboard(models.Model):
    _name = 'tt.report.dashboard'

    def get_report_json_api(self):
        return ERR.get_no_error()

    def get_report_xls_api(self):
        return ERR.get_no_error()
