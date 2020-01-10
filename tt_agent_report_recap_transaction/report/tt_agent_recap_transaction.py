from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class AgentReportRecapTransacion(models.Model):
    _name = 'report.tt_agent_report_recap_transaction.agent_report_recap'
    _description = 'Recap Transaction'

    @staticmethod
    def _select():
        return """
            rsv.id, rsv.name as order_number, rsv.issued_date as issued_date, rsv.adult, rsv.child, rsv.infant, rsv.pnr,
            rsv.total as grand_total, rsv.total_commission, rsv.total_nta, rsv.provider_name, rsv.create_date, rsv.state,
            provider_type.name as provider_type, agent.name as agent_name, agent.email as agent_email,
            currency.name as currency_name,
            agent_type.name as agent_type_name, ledger.id as ledger_id, ledger.ref as ledger_name,
            ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr,
            ledger.transaction_type as ledger_transaction_type
            """

    @staticmethod
    def _select_join_service_charge():
        return """
            rsv.id, rsv.name as order_number, rsv.pnr, rsv.total as grand_total, rsv.total_commission, rsv.total_nta, rsv.state,
            booking_ids.id as booking_id, booking_ids.pnr as booking_pnr, booking_ids.state as booking_state,
            booking_service_charge.total as booking_charge_total, booking_service_charge.charge_type as booking_charge_type
            """

    @staticmethod
    def _from(provider_type):
        # query = """tt_ledger """
        query = """tt_reservation_""" + provider_type + """ rsv """
        query += """LEFT JOIN tt_agent agent ON rsv.agent_id = agent.id
        LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = rsv.agent_type_id
        LEFT JOIN res_currency currency ON currency.id = rsv.currency_id
        RIGHT JOIN tt_ledger ledger ON ledger.res_model = rsv.res_model AND ledger.res_id = rsv.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        """
        return query

    @staticmethod
    def _from_join_service_charge(provider_type):
        query = """tt_reservation_""" + provider_type + """ rsv """
        # query += """LEFT JOIN tt_provider_""" + provider_type + """ booking_ids """
        query += """
        LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
        LEFT JOIN tt_provider_""" + provider_type + """ booking_ids ON booking_ids.booking_id = rsv.id
        LEFT JOIN tt_service_charge booking_service_charge ON booking_service_charge.provider_""" + provider_type + """_booking_id = booking_ids.id
        """
        return query

    @staticmethod
    def _where(date_from, date_to, agent_id, provider_type, state):
        where = """rsv.issued_date >= '%s' and rsv.issued_date <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        # where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if provider_type and provider_type != 'all':
            where += """ AND provider_type.code = '%s' """ % provider_type
        # where += """ AND ledger.transaction_type = 3"""
        return where

    @staticmethod
    def _where_join_service_charge(date_from, date_to, agent_id, provider_type, state):
        where = """rsv.issued_date >= '%s' and rsv.issued_date <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        # where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if provider_type and provider_type != 'all':
            where += """ AND provider_type.code = '%s' """ % provider_type
        # where += """ AND ledger.transaction_type = 3"""
        return where

    @staticmethod
    def _order_by():
        return """
        rsv.create_date, rsv.name 
        """
    @staticmethod
    def _order_by_join_service_charge():
        return """
        rsv.create_date, rsv.name
        """

    def _lines(self, date_from, date_to, agent_id, provider_type, state):
        # SELECT
        query = 'SELECT ' + self._select()

        # FROM
        query += 'FROM ' + self._from(provider_type)

        # WHERE
        query += 'WHERE ' + self._where(date_from, date_to, agent_id, provider_type, state)

        # 'GROUP BY' + self._group_by() + \
        query += 'ORDER BY ' + self._order_by()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _lines_join_service_charge(self, date_from, date_to, agent_id, provider_type, state):
        # SELECT
        query = 'SELECT ' + self._select_join_service_charge()

        # FROM
        query += 'FROM ' + self._from_join_service_charge(provider_type)

        # WHERE
        query += 'WHERE ' + self._where_join_service_charge(date_from, date_to, agent_id, provider_type, state)

        # ORDER BY
        query += 'ORDER BY ' + self._order_by_join_service_charge()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _get_lines_data(self, date_from, date_to, agent_id, provider_type, state):
        lines = []
        if provider_type != 'all':
            lines = self._lines(date_from, date_to, agent_id, provider_type, state)
            lines = self._convert_data(lines, provider_type)
        else:
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines(date_from, date_to, agent_id, provider_type, state)
                report_lines = self._convert_data(report_lines, provider_type)
                for line in report_lines:
                    lines.append(line)
        return lines

    def _get_lines_data_join_service_charge(self, date_from, date_to, agent_id, provider_type, state):
        lines = []
        if provider_type != 'all':
            lines = self._lines_join_service_charge(date_from, date_to, agent_id, provider_type, state)
        else:
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines_join_service_charge(date_from, date_to, agent_id, provider_type, state)
                for j in report_lines:
                    lines.append(j)
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _convert_data(self, lines, provider_type):
        for rec in lines:
            rec['create_date'] = self._datetime_user_context(rec['create_date'])
            try:
                rec['issued_date'] = self._datetime_user_context(rec['issued_date'])
            except:
                pass
            # rec['state'] = variables.BOOKING_STATE_STR[rec['state']] if rec['state'] else ''  # STATE_OFFLINE_STR[rec['state']]
        return lines


    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Recap Transaction Report: ' + data_form['subtitle']

    def _prepare_values(self, data_form):
        data_form['state'] = 'issued'
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        # if not data_form['state']:
        #     data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        state = data_form['state']
        provider_type = data_form['provider_type']
        # lines = self._get_lines_data_search(date_from, date_to, agent_id, provider_type, state)
        lines = self._get_lines_data(date_from, date_to, agent_id, provider_type, state)
        second_lines = self._get_lines_data_join_service_charge(date_from, date_to, agent_id, provider_type, state)
        # second_lines = []
        self._report_title(data_form)

        return {
            'lines': lines,
            'second_lines': second_lines,
            'data_form': data_form
        }
