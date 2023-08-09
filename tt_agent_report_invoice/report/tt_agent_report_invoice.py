from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class AgentReportInvoice(models.Model):
    _name = 'report.tt_agent_report_invoice.agent_report_invoice'
    _description = 'Invoice Report'

    @staticmethod
    def _select():
        # return """* """
        return """
        invoice.id as invoice_id,
        invoice.date_invoice, invoice.name as invoice_number, invoice.total as invoice_total,
        invoice.state, invoice.payment_acquirers as payment_acquirers, billing.name as billing_statement,
        agent.name as agent_name, agent_type.name as agent_type,
        customer.name as booker_name,
        customer_parent.name as customer_name,
        customer_type.name as customer_type,
        invoice_detail.name as invoice_line, invoice_detail.total as invoice_line_total, invoice_detail.reference as invoice_line_reference,
        payment.reference as payment_ref, payment_invoice.pay_amount as payment_pay_amount,
        acquirer.name as payment_acquirer, acquirer.account_number as payment_acquirer_account_number,
        users.login as user_name
        """

    @staticmethod
    def _from():
        # return """tt_agent_invoice invoice """
        return """ tt_agent_invoice invoice
        LEFT JOIN tt_agent_invoice_line invoice_detail ON invoice.id = invoice_detail.invoice_id
        LEFT JOIN tt_agent agent ON invoice.agent_id = agent.id
        LEFT JOIN tt_billing_statement billing ON invoice.billing_statement_id = billing.id
        LEFT JOIN tt_agent_type agent_type ON agent.agent_type_id = agent_type.id
        LEFT JOIN tt_customer customer ON invoice.booker_id = customer.id
        LEFT JOIN tt_customer_parent customer_parent ON invoice.customer_parent_id = customer_parent.id
        LEFT JOIN tt_customer_parent_type customer_type ON customer_parent.customer_parent_type_id = customer_type.id
        LEFT JOIN tt_payment_invoice_rel payment_invoice ON payment_invoice.invoice_id = invoice.id
        LEFT JOIN tt_payment payment ON payment.id = payment_invoice.payment_id
        LEFT JOIN payment_acquirer acquirer ON payment.acquirer_id = acquirer.id
        LEFT JOIN res_users users ON payment.approve_uid = users.id
        """

    STATE = [
        ('all', 'All'),
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('bill', 'Bill'),
        ('bill2', 'Bill by System'),
        ('cancel', 'Canceled')
    ]

    @staticmethod
    def _where(date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        where = """invoice.create_date >= '%s' and invoice.create_date <= '%s'""" % (date_from, date_to)
        if state == 'draft':
            where += """ AND invoice.state IN ('draft')"""
        if state == 'paid':
            where += """ AND invoice.state IN ('paid')"""
        if state == 'bill':
            where += """ AND invoice.state IN ('bill')"""
        if state == 'bill2':
            where += """ AND invoice.state IN ('bill2')"""
        if state == 'cancel':
            where += """ AND invoice.state IN ('cancel')"""
        if ho_id:
            where += """ AND invoice.ho_id = %s """ % ho_id
        if agent_id:
            where += """ AND invoice.agent_id = %s """ % agent_id
        if customer_parent_id:
            where += """ AND invoice.customer_parent_id = %s """ % customer_parent_id
        return where

    @staticmethod
    def _order_by():
        return """ invoice.create_date """

    def _lines(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        # SELECT
        query = 'SELECT ' + self._select()

        # FROM
        query += 'FROM ' + self._from()

        # WHERE
        query += 'WHERE ' + self._where(date_from, date_to, agent_id, ho_id, customer_parent_id, state)

        #ORDER BY
        query += 'ORDER BY ' + self._order_by()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _convert_data(self, lines):
        for i in lines:
            i['date_invoice'] = self._datetime_user_context(i['date_invoice'])
            # i['create_date'] = self._datetime_user_context(i['create_date'])

        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _get_lines_data(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, state)
        lines = self._convert_data(lines)
        # lines = []
        # if state != 'all':
        #     lines = self._lines(date_from, date_to, agent_id, state)
        #     lines = self._convert_data(lines)
        # else:
        #     states = ['draft', 'paid', 'bill', 'bill2', 'cancel']
        #     for i in states:
        #         line = self._lines(date_from, date_to, agent_id, i)
        #         line = self._convert_data(line)
        #         for j in line:
        #             lines.append(j)
        return lines

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Invoice Report: ' + data_form['subtitle']

    # main process function
    def _prepare_valued(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        ho_id = data_form['ho_id']
        agent_id = data_form['agent_id']
        customer_parent_id = data_form['customer_parent_id']
        state = data_form['state']
        # provider_type = data_form['provider_type']
        # line = self._get_lines_data(date_from, date_to, agent_id, provider_type, state)
        line = self._get_lines_data(date_from, date_to, agent_id, ho_id, customer_parent_id, state)
        # line.sort(key=lambda x: x['invoice_id'])
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('data_form'):
            raise UserError(_("Form content is missing,this report cannot be printed"))

        docs = self._prepare_valued(data['data_form'])
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': docs
        }








