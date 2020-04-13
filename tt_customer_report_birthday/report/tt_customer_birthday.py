from odoo import models, fields
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class CustomerRerportBirthday(models.Model):
    _name = 'report.tt_customer_report_birthday.customer_report_birthday'
    _description = 'customer birthday list'

    @staticmethod
    def _select():
        return """customer.name as customer_name,
        customer.birth_date as customer_birthdate,
        EXTRACT (DAY FROM customer.birth_date) as customer_birthday,
        EXTRACT (MONTH FROM customer.birth_date) as customer_birthmonth, 
        EXTRACT (YEAR FROM customer.birth_date) as customer_birthyear,
        customer.gender as customer_gender,
        customer.active as customer_active,
        customer.agent_id as agent_id
        """

    @staticmethod
    def _from():
        return """tt_customer customer
        """

    @staticmethod
    def _where(month_from, month_to, agent_id):
        if month_from > month_to:
            where = """EXTRACT (MONTH FROM customer.birth_date) >= '%s' AND EXTRACT (MONTH FROM customer.birth_date) <= 12""" %(month_from)
            where += """ OR EXTRACT (MONTH FROM customer.birth_date) <= '%s'""" %(month_to)
        else:
            where = """EXTRACT (MONTH FROM customer.birth_date) >= '%s' AND EXTRACT (month FROM customer.birth_date) <= '%s'""" % (month_from, month_to)
        where += """ AND customer.active = True"""
        where += """ AND customer.agent_id = %s""" % agent_id
        return where

    @staticmethod
    def _order_by():
        return """EXTRACT (MONTH FROM customer.birth_date), EXTRACT (DAY FROM customer.birth_date)
        """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Birthday Report: ' + data_form['subtitle']

    def _lines(self, month_from, month_to, agent_id):
        query = "SELECT {} FROM {} WHERE {} ORDER BY {}".format(self._select(), self._from(), self._where(month_from, month_to, agent_id), self._order_by())

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _convert_data(self, lines):
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _get_lines_data(self, date_from, date_to, agent_id):
        lines = self._lines(date_from, date_to, agent_id)
        # lines = self._convert_data(lines)
        return lines

    def _prepare_valued(self, data_form):
        month_from = data_form['month_from']
        month_to = data_form['month_to']
        agent_id = data_form['agent_id']
        line = self._get_lines_data(month_from, month_to, agent_id)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }