from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
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

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime("%Y-%m-%d")

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
        query = "SELECT agent.seq_id, agent.name, agent.agent_type_id FROM tt_agent agent ORDER BY name"

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def get_agent_type_lines(self):
        query = "SELECT agent.name, agent.code ,agent.id FROM tt_agent_type agent ORDER BY name"

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def get_provider_lines(self):
        query = "SELECT provider.name, provider.code, provider_type.name as provider_type FROM tt_provider provider JOIN tt_provider_type provider_type ON provider.provider_type_id = provider_type.id ORDER BY name"

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def get_carrier_lines(self):
        query = ""

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def get_profit_lines(self, data):
        query = """
        SELECT ledger.date as date_og, ledger.debit, agent.name as agent_name, agent_type.name as agent_type, provider_type.name as provider_type
        FROM tt_ledger ledger 
        LEFT JOIN tt_agent agent ON agent.id = ledger.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = ledger.agent_type_id
        LEFT JOIN tt_provider_type provider_type ON provider_type.id = ledger.provider_type_id
        WHERE ledger.name LIKE 'Commission%' AND ledger.create_date >= '{}' AND ledger.create_date <= '{}' AND ledger.is_reversed = 'FALSE'
        """.format(data['start_date'], data['end_date'])

        if data['agent_type_seq_id']:
            query += """AND agent_type.code = '%s' """ % (data['agent_type_seq_id'])

        if data['agent_seq_id']:
            query += """AND agent.seq_id = '%s' """ % (data['agent_seq_id'])

        if data['provider_type']:
            query += """AND provider_type.code = '%s' """ % (data['provider_type'])

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

    def _convert_data_profit(self, lines):
        for i in lines:
            i['date'] = self._datetime_user_context(i['date_og'])

            temp_booked_date = i['date'].split("-")
            i['year'] = temp_booked_date[0]
            i['month'] = temp_booked_date[1]
        return lines

    def get_agent_all(self):
        lines = self.get_agent_lines()
        lines.insert(0, {'seq_id': '', 'name': 'All', 'agent_type_id': ''})
        return lines

    def get_agent_type_all(self):
        lines = self.get_agent_type_lines()
        return lines

    def get_provider_all(self):
        lines = self.get_provider_lines()
        lines.insert(0, {'name': 'All Provider', 'code': '', 'provider_type': ''})
        return lines

    def get_carrier(self):
        lines = self.get_carrier_lines()
        return lines

    def get_profit(self, data):
        # proceed something
        if data['provider_type'] != 'overall':
            provider = data['provider_type'].split("_")
            data['provider_type'] = provider[1]
        else:
            data['provider_type'] = ''

        lines = self.get_profit_lines(data)
        lines = self._convert_data_profit(lines)

        return lines