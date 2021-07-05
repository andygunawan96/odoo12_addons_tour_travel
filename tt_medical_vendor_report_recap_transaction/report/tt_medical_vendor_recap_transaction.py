from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class MedicalVendorReportRecapTransacion(models.Model):
    _name = 'report.tt_report_recap_transaction.medical_vendor'
    _description = 'Recap Transaction'

    ################
    #   All of select function to build SELECT function in SQL
    ################

    # this select function responsible to build query to produce the neccessary report
    @staticmethod
    def _select():
        return """
            rsv.id as rsv_id, rsv.name as order_number, rsv.state as state, rsv.adult as adult, rsv.state_vendor as state_vendor, 
            rsv.provider_name as provider_name, provider_type.name as provider_type, carrier.name as carrier_name, 
            timeslot.datetimeslot as test_datetime
            """

    # this select function responsible build query for passengers
    @staticmethod
    def _select_join_passengers():
        return """
            psg.booking_id as booking_id, psg.title as title, psg.first_name as first_name, psg.last_name as last_name, 
            psg.birth_date as birth_date, psg.nomor_karcis as nomor_karcis, psg.nomor_perserta as nomor_perserta
            """

    ################
    #   All of FROM function to build FROM function in SQL
    #   name of the function correspond to respected SELECT functions for easy development
    ################
    @staticmethod
    def _from(provider_type):
        # query = """tt_ledger """
        query = """tt_reservation_""" + provider_type + """ rsv """
        query += """LEFT JOIN tt_agent agent ON rsv.agent_id = agent.id
        LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
        LEFT JOIN tt_transport_carrier carrier ON carrier.code = rsv.carrier_name
        """
        query += """LEFT JOIN tt_timeslot_""" + provider_type + """ timeslot ON timeslot.id = rsv.picked_timeslot_id """
        return query

    @staticmethod
    def _from_join_passengers(provider_type):
        query = """tt_reservation_passenger_""" + provider_type + """ psg """
        query += """LEFT JOIN tt_reservation_""" + provider_type + """ rsv ON rsv.id = psg.booking_id """
        query += """LEFT JOIN tt_agent agent ON rsv.agent_id = agent.id
                LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
                LEFT JOIN tt_transport_carrier carrier ON carrier.code = rsv.carrier_name
                """
        query += """LEFT JOIN tt_timeslot_""" + provider_type + """ timeslot ON timeslot.id = rsv.picked_timeslot_id """
        return query

    ################
    #   All of WHERE function to build WHERE function in SQL
    #   name of the function correspond to respected SELECT, FORM functions for easy development
    ################
    @staticmethod
    def _where(date_from, date_to, agent_id, provider_type, state):
        where = """test_datetime >= '%s' and test_datetime <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        # where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if provider_type and provider_type != 'all':
            where += """ AND provider_type.code = '%s' """ % provider_type
        if state:
            where += """ AND (rsv.state = '%s' OR rsv.state = 'reissue') """ % state
        return where

    @staticmethod
    def _where_join_passengers(date_from, date_to, agent_id, provider_type, state):
        where = """test_datetime >= '%s' and test_datetime <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        # where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if provider_type and provider_type != 'all':
            where += """ AND provider_type.code = '%s' """ % provider_type
        if state:
            where += """ AND (rsv.state = '%s' OR rsv.state = 'reissue') """ % state
        return where

    ################
    #   All of ORDER function to build ORDER BY function in SQL
    #   name of the function correspond to respected SELECT, FORM, WHERE, GROUP BY functions for easy development
    ################
    @staticmethod
    def _order_by():
        return """
        test_datetime, rsv.name
        """

    @staticmethod
    def _order_by_join_passengers():
        return """
            psg.name
            """

    ################
    #   Function to build the full query
    #   Within this function we will call the SELECT function, FROM function, WHERE function, etc
    #   for more information of what each query do, se explanation above every select function
    #   name of select function is the same as the _lines_[function name] or get_[function_name]
    ################
    def _lines(self, date_from, date_to, agent_id, provider_type, state):
        # SELECT
        query = 'SELECT ' + self._select()
        if provider_type == 'offline':
            query += self._offline()

        # FROM
        query += 'FROM ' + self._from(provider_type)

        # WHERE
        query += 'WHERE ' + self._where(date_from, date_to, agent_id, provider_type, state)

        # 'GROUP BY' + self._group_by() + \
        query += 'ORDER BY ' + self._order_by()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _lines_join_passengers(self, date_from, date_to, agent_id, provider_type, state):
        # SELECT
        query = 'SELECT ' + self._select_join_passengers()

        # FROM
        query += 'FROM ' + self._from_join_passengers(provider_type)

        # WHERE
        query += 'WHERE ' + self._where_join_passengers(date_from, date_to, agent_id, provider_type, state)

        # ORDER BY
        query += 'ORDER BY ' + self._order_by_join_passengers()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function handle preparation to call query builder for service charge
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

    # this function handle preparation to call query builder for service charge
    def _get_lines_data_join_passengers(self, date_from, date_to, agent_id, provider_type, state):
        lines = []
        if provider_type != 'all':
            lines = self._lines_join_passengers(date_from, date_to, agent_id, provider_type, state)
        else:
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines_join_passengers(date_from, date_to, agent_id, provider_type, state)
                for j in report_lines:
                    lines.append(j)
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _convert_data(self, lines, provider_type):
        for rec in lines:
            try:
                rec['test_datetime'] = self._datetime_user_context(rec['test_datetime'])
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
        second_lines = self._get_lines_data_join_passengers(date_from, date_to, agent_id, provider_type, state)
        self._report_title(data_form)

        return {
            'lines': lines,
            'second_lines': second_lines,
            'data_form': data_form
        }
