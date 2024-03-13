from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class CustomerParentReportBalance(models.Model):
    _name = 'report.tt_agent_report_balance.customer_parent_report_balance'
    _description = "Customer Parent Balance Report"

    @staticmethod
    def _select():
        return """
        customer_parent.name as customer_parent_name, customer_parent.balance as customer_parent_balance, customer_parent.active as customer_parent_status,
        customer_parent.credit_limit as customer_parent_credit_limit, customer_parent.actual_balance as customer_parent_actual_balance, 
        customer_parent.unprocessed_amount as customer_parent_credit_unprocessed, customer_parent_type.name as customer_parent_type_name,
        currency.name as currency_name
        """
        # return """*"""

    @staticmethod
    def _from():
        return """tt_customer_parent customer_parent
        LEFT JOIN tt_customer_parent_type customer_parent_type ON customer_parent.customer_parent_type_id = tt_customer_parent_type.id
        LEFT JOIN res_currency currency ON currency.id = customer_parent.currency_id
        """

    @staticmethod
    def _where(agent_id, ho_id, customer_parent_id, customer_parent_type_ids):
        where = """customer_parent.active = True AND customer_parent_type.id in %s""" % (str(customer_parent_type_ids).replace('[', '(').replace(']', ')'))
        if ho_id:
            where += """ AND customer_parent.ho_id = """ + str(ho_id)
        if agent_id:
            where += """ AND customer_parent.parent_agent_id = """ + str(agent_id)
        if customer_parent_id:
            where += """ AND customer_parent.id = """ + str(customer_parent_id)
        return where

    @staticmethod
    def _order_by():
        return """customer_parent_type.id, customer_parent.id
        """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Customer Parent Balance Report: ' + data_form['subtitle']

    def _lines(self, date_from, date_to, agent_id, ho_id, customer_parent_id, customer_parent_type_ids):
        query = 'SELECT {} FROM {} WHERE {} ORDER BY {}'.format(self._select(), self._from(), self._where(agent_id, ho_id, customer_parent_id, customer_parent_type_ids), self._order_by())

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

    def _get_lines_data(self, date_from, date_to, agent_id, ho_id, customer_parent_id, customer_parent_type_ids):
        lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, customer_parent_type_ids)
        # lines = self._convert_data(lines)
        return lines

    def _prepare_valued(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        ho_id = data_form['ho_id']
        agent_id = data_form['agent_id']
        customer_parent_id = data_form['customer_parent_id']
        customer_parent_type_ids = [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id]
        line = self._get_lines_data(date_from, date_to, agent_id, ho_id, customer_parent_id, customer_parent_type_ids)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }

    def _search_valued(self, data_form):
        search_list = [('state', '=', 'done'), ('customer_parent_type_id', 'in', [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id])]
        if data_form['ho_id']:
            search_list.append(('ho_id', '=', data_form['ho_id']))
        if data_form['agent_id']:
            search_list.append(('parent_agent_id', '=', data_form['agent_id']))
        if data_form['customer_parent_id']:
            search_list.append(('id', '=', data_form['customer_parent_id']))
        data = self.env['tt.customer.parent'].sudo().search(search_list, order='customer_parent_type_id').read()
        line = []
        for i in data:
            temp_dict = {
                'customer_parent_name': i['name'],
                'customer_parent_type_name': i['customer_parent_type_id'][1],
                'currency_name': i['currency_id'][1],
                'customer_parent_balance': i['balance'],
                'customer_parent_credit_limit': i['credit_limit'],
                'customer_parent_actual_balance': i['actual_balance'],
                'customer_parent_credit_unprocessed': i['unprocessed_amount'],
                'customer_parent_status': i['active']
            }
            line.append(temp_dict)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }
