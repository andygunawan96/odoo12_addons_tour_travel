from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class AgentReportBalance(models.Model):
    _name = 'report.tt_agent_report_balance.agent_report_balance'
    _description = "Agent Balance Report"

    @staticmethod
    def _select():
        return """
        agent.name as agent_name, agent.balance as agent_balance, agent.active as agent_status,
        agent.credit_limit as agent_credit_limit, agent.actual_credit_balance as agent_actual_credit_balance, 
        agent.unprocessed_amount as agent_credit_unprocessed, agent.balance_credit_limit as agent_balance_credit_limit,
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
    def _where(agent_id, ho_id):
        where = """agent.active = True"""
        if ho_id:
            where += """ AND agent.ho_id = """ + str(ho_id)
        if agent_id:
            where += """ AND agent.id = """ + str(agent_id)
        return where

    @staticmethod
    def _order_by():
        return """agent_type.id, agent.id
        """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Agent Balance Report: ' + data_form['subtitle']

    def _lines(self, date_from, date_to, agent_id, ho_id):
        query = 'SELECT {} FROM {} WHERE {} ORDER BY {}'.format(self._select(), self._from(), self._where(agent_id, ho_id), self._order_by())

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

    def _get_lines_data(self, date_from, date_to, agent_id, ho_id):
        lines = self._lines(date_from, date_to, agent_id, ho_id)
        # lines = self._convert_data(lines)
        return lines

    def _prepare_valued(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        ho_id = data_form['ho_id']
        agent_id = data_form['agent_id']
        line = self._get_lines_data(date_from, date_to, agent_id, ho_id)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }

    def _search_valued(self, data_form):
        search_list = []
        if data_form['ho_id']:
            search_list.append(('ho_id', '=', data_form['ho_id']))
        if data_form['agent_id']:
            search_list.append(('id', '=', data_form['agent_id']))
        data = self.env['tt.agent'].sudo().search(search_list, order='agent_type_id').read()
        line = []
        for i in data:
            temp_dict = {
                'agent_name': i['name'],
                'agent_type_name': i['agent_type_id'][1],
                'currency_name': i['currency_id'][1],
                'agent_balance': i['balance'],
                'agent_credit_limit': i['credit_limit'],
                'agent_actual_credit_balance': i['actual_credit_balance'],
                'agent_credit_unprocessed': i['unprocessed_amount'],
                'agent_balance_credit_limit': i['balance_credit_limit'],
                'agent_status': i['active']
            }
            line.append(temp_dict)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }
