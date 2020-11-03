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
    def _select_top_up():
        return """
        topup.validated_amount
        """

    @staticmethod
    def _select_payment():
        return """ COUNT (payment_method)
        """

    @staticmethod
    def _from_top_up():
        return """
        tt_top_up topup
        """

    @staticmethod
    def _from_payment():
        return """ tt.reservation
        """

    @staticmethod
    def _where_top_up(start_date):
        return """
        topup.approve_date = '%s'
        """ % (start_date)

    @staticmethod
    def _where_payment(start_date, end_date):
        return """
        reservation.issued_date >= '%s' AND reservation.issued_date <= '%s' AND reservation.state == 'issued'
        """ % (start_date, end_date)

    @staticmethod
    def _group_by_payment():
        return """ payment_method
        """

    def get_top_up(self, start_date, end_date):
        query = "SELECT " + self._select_top_up() + "FROM " + self._from_top_up() + "WHERE " + self._where_top_up()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def get_payment_report(self, start_date, end_date):
        query = "SELECT " + self._selet_payment() + "FROM " + self._from_payment() + "WHERE " + self._where_payment(start_date, end_date) + "GROUP BY " + self._group_by_payment()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def get_agent_lines(self):
        query = "SELECT agent.id, agent.name, agent.agent_type_id FROM tt_agent agent"

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _get_reports(self, data):
        date_from = data['start_date']
        date_to = data['end_date']
        search_type = data['type']
        if search_type == 'top_up':
            lines = self.get_top_up(date_from, date_to)
        elif search_type == 'payment':
            lines = self.get_payment_report(date_from, date_to)
        elif search_type == 'cash_report':
            lines = self.get_cash_report(date_from, date_to)
        else:
            lines = []
        return {
            'lines': lines
        }

