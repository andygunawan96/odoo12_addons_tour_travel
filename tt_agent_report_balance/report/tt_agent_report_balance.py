from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class AgentReportBalance(models.Model):
    _name = 'report.tt_agent_report_balance.agent_report_balance'
    _description = "Balance Report"

    @staticmethod
    def _select():
        return """
        agent.name as agent_name, agent.balance as agent_balance, agent.active as agent_status,
        agent_type.name as agent_type_name,
        currency.name as currency_name        
        """
        # return """*"""

    @staticmethod
    def _from():
        return """tt_agent agent
        LEFT JOIN tt_agent_type agent_type ON agent.agent_type_id = agent_type.id
        LEFT JOIN res_currency currency ON currency.id = agent.currency_id
        """

    @staticmethod
    def _where(date_from, date_to):
        where = """agent.create_date >= '%s' and agent.create_date <= '%s'""" % (date_from, date_to)
        return where

    @staticmethod
    def _order_by():
        return """agent.id
        """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Balance Report: ' + data_form['subtitle']

    def _lines(self, date_from, date_to, agent_id):
        query = 'SELECT {} FROM {} ORDER BY {}'.format(self._select(), self._from(), self._order_by())

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _convert_data(self, lines):
        for i in lines:
            i['create_date'] = self._datetime_user_context(i['create__date'])
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self,value).strftime('%Y-%m-%d %H:%M:%S')

    def _get_lines_data(self, date_from, date_to, agent_id):
        lines = self._lines(date_from, date_to, agent_id)
        # lines = self._convert_data(lines)
        return lines

    def _prepare_valued(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        line = self._get_lines_data(date_from, date_to, agent_id)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }

    def _search_valued(self, data_form):
        data = self.env['tt.agent'].sudo().search([]).read()
        line = []
        for i in data:
            temp_dict = {
                'agent_name': i['name'],
                'agent_type_name': i['agent_type_id'][1],
                'currency_name': i['currency_id'][1],
                'agent_balance': i['balance'],
                'agent_status': i['active']
            }
            line.append(temp_dict)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }