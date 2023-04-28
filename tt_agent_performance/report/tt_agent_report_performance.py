from odoo import models, fields
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class AgentReportPerformance(models.Model):
    _name = 'report.tt_agent_report_performance.agt_report_prf'
    _description = "Agent performance Report"

    @staticmethod
    def _select():
        return """
        sales.total as sales_total, sales.total_after_tax as sales_total_after_tax,
        agent.id as agent_id,
        agent.name as agent_name, agent.email as agent_email,
        parent_agent.name as parent_agent_name,
        agent_type.name as agent_type_name,
        agent_type.code as agent_type_code,
        phone.phone_number as phone_number
        """
    @staticmethod
    def _from():
        return """
        tt_agent_invoice sales
        LEFT JOIN tt_agent agent ON sales.agent_id = agent.id
        LEFT JOIN tt_agent parent_agent ON agent.parent_agent_id = parent_agent.id
        LEFT JOIN tt_agent_type agent_type ON agent.agent_type_id = agent_type.id
        LEFT JOIN phone_detail phone ON phone.agent_id = agent.id
        """

    @staticmethod
    def _where(date_from, date_to, agent_type, ho_id):
        where = """sales.create_date >= '{}' AND sales.create_date <= '{}' """.format(date_from, date_to)
        where += """AND sales.state != 'cancel'"""
        if ho_id:
            where += """ AND sales.ho_id = """ + str(ho_id)
        if agent_type != 'all':
            where += """ AND agent_type.code = '{}'""".format(agent_type)
        return where

    @staticmethod
    def _order_by():
        return """agent.id
        """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Performance Report: ' + data_form['subtitle']

    def _lines(self, date_from, date_to, agent_type, ho_id):
        query = "SELECT {} FROM {} WHERE {} ORDER BY {}".format(self._select(), self._from(), self._where(date_from, date_to, agent_type, ho_id), self._order_by())

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _convert_data(self, lines):
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d')

    def _get_lines_data(self, date_from, date_to, agent_type, ho_id):
        lines = self._lines(date_from, date_to, agent_type, ho_id)
        return lines

    def _prepare_valued(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        ho_id = data_form['ho_id']
        if not data_form['state']:
            data_form['state'] = 'all'
        agent_type = data_form['agent_type']
        line = self._get_lines_data(date_from, date_to, agent_type, ho_id)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }