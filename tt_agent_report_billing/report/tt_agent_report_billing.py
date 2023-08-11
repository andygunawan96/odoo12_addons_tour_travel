from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class AgentReportBilling(models.Model):
    _name = 'report.tt_agent_report_billing.agent_report_billing'
    _description = "Billing Report"

    @staticmethod
    def _select():
        return """billing.name as billing_number, billing.date_billing as billing_date, billing.due_date as billing_due_date,
        billing.state as billing_state,
        agent.name as agent_name,
        invoice.total as invoice_amount, invoice.name as invoice_number,
        payment.name as payment_number,
        customer.name as customer_name, customer_type.name as customer_type_name
        """

    @staticmethod
    def _select_more():
        return """billing.name as billing_number, 
        invoice.total as invoice_total
        """

    @staticmethod
    def _from():
        return """tt_billing_statement billing 
        LEFT JOIN tt_agent agent ON billing.agent_id = agent.id
        LEFT JOIN tt_agent_invoice invoice ON billing.id = invoice.billing_statement_id
        LEFT JOIN tt_customer_parent customer ON billing.customer_parent_id = customer.id
        LEFT JOIN tt_customer_parent_type customer_type ON billing.customer_parent_type_id = customer_type.id
        LEFT JOIN tt_payment_invoice_rel payment_ids ON invoice.id = payment_ids.invoice_id
        LEFT JOIN tt_payment payment ON payment_ids.payment_id = payment.id
        """

    @staticmethod
    def _from_more():
        return """tt_billing_statement billing
        LEFT JOIN tt_agent_invoice invoice ON billing.id = invoice.billing_statement_id
        LEFT JOIN tt_payment_invoice_rel payment_ids ON invoice.id = payment_ids.invoice_id
        LEFT JOIN tt_payment payment ON payment_ids.payment_id = payment.id
        """

    @staticmethod
    def _where(date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        where = """billing.create_date >= '%s' and billing.create_date <= '%s'""" % (date_from, date_to)
        if state == 'draft':
            where += """ AND billing.state IN ('draft')"""
        if state == 'paid':
            where += """ AND billing.state IN ('paid')"""
        if state == 'confirm':
            where += """ AND billing.state IN ('confirm')"""
        if state == 'partial':
            where += """ AND billing.state IN ('partial')"""
        if state == 'cancel':
            where += """ AND billing.state IN ('cancel')"""
        if ho_id:
            where += """ AND billing.ho_id = %s""" % ho_id
        if agent_id:
            where += """ AND billing.agent_id = %s""" % agent_id
        if customer_parent_id:
            where += """ AND billing.customer_parent_id = %s""" % customer_parent_id
        return where

    @staticmethod
    def _order_by():
        return """ billing.id """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Billing Report: ' + data_form['subtitle']

    def _lines(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        query = 'SELECT ' + self._select()
        query += 'FROM ' + self._from()
        query += 'WHERE ' + self._where(date_from, date_to, agent_id, ho_id, customer_parent_id, state)
        query += ' ORDER BY ' + self._order_by()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _lines_more(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        query = "SELECT {} FROM {} WHERE {} ORDER BY {}".format(self._select_more(), self._from_more(), self._where(date_from, date_to, agent_id, ho_id, customer_parent_id, state), self._order_by())

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _convert_data(self, lines):
        for i in lines:
            i['billing_date'] = self._datetime_user_context(i['billing_date'])
            i['billing_due_date'] = self._datetime_user_context(i['billing_due_date'])

        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self,value).strftime('%Y-%b-%d')

    def _get_lines_data(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, state)
        lines = self._convert_data(lines)
        # lines = []
        # if state != 'all':
        #     lines = self._lines(date_from, date_to, agent_id, state)
        #     lines = self._convert_data(lines)
        # else:
        #     states = ['all', 'draft', 'confirm', 'partial', 'paid', 'cancel']
        #     for i in states:
        #         line = self._lines(date_from, date_to, agent_id, i)
        #         line = self._convert_data(line)
        #         for j in line:
        #             lines.append(j)
        return lines

    def _get_lines_data_more(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        lines = []
        if state != 'all':
            lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, state)
        else:
            states = ['all', 'draft', 'confirm', 'partial', 'paid', 'cancel']
            for i in states:
                line = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, i)
                line = self._convert_data(line)
                for j in line:
                    lines.append(j)
        return lines

    def _prepare_valued(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        ho_id = data_form['ho_id']
        customer_parent_id = data_form['customer_parent_id']
        state = data_form['state']
        line = self._get_lines_data(date_from, date_to, agent_id, ho_id, customer_parent_id, state)
        second_line = self._lines_more(date_from, date_to, agent_id, ho_id, customer_parent_id, state)
        self._report_title(data_form)
        return {
            'lines': line,
            'second_line': second_line,
            'data_form': data_form
        }
