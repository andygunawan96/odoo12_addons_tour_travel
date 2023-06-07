from odoo import models, fields

import logging
_logger = logging.getLogger(__name__)

class CustomerRerportPassportExpiration(models.Model):
    _name = 'report.tt_customer_passport_expiration.passport_expiration'
    _description = 'customer passport expiration list'

    @staticmethod
    def _select():
        return """
        customer.seq_id as customer_seq_id,
        customer.name as customer_name,
        cidentity.identity_type as identity_type,
        cidentity.identity_number as identity_number,
        cidentity.identity_expdate as identity_expdate,
        agent.name as agent_name
        """

    @staticmethod
    def _from():
        return """tt_customer customer LEFT JOIN tt_agent agent ON customer.agent_id = agent.id
        LEFT JOIN tt_customer_identity cidentity ON cidentity.customer_id = customer.id
        """

    @staticmethod
    def _where(date_before, agent_id, ho_id):
        where = """cidentity.identity_type = 'passport' AND cidentity.identity_expdate <= '%s'""" % (date_before)
        where += """ AND customer.active = True"""
        if ho_id:
            where += """ AND customer.ho_id = %s""" % ho_id
        if agent_id:
            where += """ AND customer.agent_id = %s""" % agent_id
        return where

    @staticmethod
    def _order_by():
        return """agent_name, identity_expdate
        """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Passport Expiration Report: ' + data_form['subtitle']

    def _lines(self, date_before, agent_id, ho_id):
        query = "SELECT {} ".format(self._select())
        query += "FROM {} ".format(self._from())
        query += "WHERE {} ".format(self._where(date_before, agent_id, ho_id))
        query += "ORDER BY {}".format(self._order_by())

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _convert_data(self, lines):
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _get_lines_data(self, date_before, agent_id, ho_id):
        lines = self._lines(date_before, agent_id, ho_id)
        # lines = self._convert_data(lines)
        return lines

    def _prepare_valued(self, data_form):
        date_befre = data_form['date_before']
        agent_id = data_form['agent_id']
        ho_id = data_form['ho_id']
        line = self._get_lines_data(date_befre, agent_id, ho_id)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }
