from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class ReportDashboardOverall(models.Model):
    _name = 'report.tt_report_dashboard.overall'
    _description = 'Recap Reservation'

    @staticmethod
    def _select():
        return """ """

    @staticmethod
    def _from():
        return """ """

    @staticmethod
    def _where():
        return """ """

    def _get_lines(self, start_date, end_date):
        query = "SELECT " + self._select() + "FROM " + self._from() + "WHERE " + self._where()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _get_value(self, start_date, end_date):
        lines = self._get_lines(start_date, end_date)
        return lines

