from odoo import models, fields
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class CustomerReportPerformance(models.Model):
    _name = 'report.tt_customer_report_performance.cust_report_prf'
    _description = 'Customer performance report'

    @staticmethod
    def _select():
        return """
        reservation.name as reservation_name, reservation.provider_name as reservation_provider_name, 
        reservation.carrier_name as reservation_carrier_name,
        reservation.payment_method as reservation_payment_method,
        reservation.total as charge_total,
        provider_type.name as provider_type_name,
        customer.name as customer_name,  customer.gender as customer_gender, 
        customer.nationality_id, customer.seq_id as customer_seq_id,
        currency.name as currency_name
        """

    @staticmethod
    def _from(provider_type):
        _logger.info(provider_type)
        query = ''
        # if provider_type == 'visa' or provider_type == 'passport':
        #     query = """tt_reservation_""" + provider_type + """_order_passengers customer """
        #     query += """LEFT JOIN tt_reservation_""" + provider_type + """ reservation ON customer.booking_id = reservation.id"""
        # else:
        query += """tt_reservation_""" + provider_type + """ reservation """
        query += """LEFT JOIN tt_customer customer ON customer.id = reservation.booker_id """
        query += """LEFT JOIN tt_provider_type provider_type ON provider_type.id = reservation.provider_type_id """
        query += """LEFT JOIN res_currency currency ON currency.id = reservation.currency_id"""

        return query

    @staticmethod
    def _where(date_from, date_to, agent_id, provider_type, ho_id, customer_parent_id):
        where = """reservation.create_date >= '{}' AND reservation.create_date <= '{}'""".format(date_from, date_to)
        where += """AND reservation.state = 'issued'"""
        if ho_id:
            where += """ AND reservation.ho_id = %s""" % ho_id
        if agent_id:
            where += """ AND reservation.agent_id = %s""" % agent_id
        if customer_parent_id:
            where += """ AND reservation.customer_parent_id = %s""" % customer_parent_id
        # if provider_type != 'offline':
        #     where += """ AND reservation.provider_type = '%s' """ % provider_type
        return where

    @staticmethod
    def _order_by():
        return """reservation.date
        """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Performance Report: ' + data_form['subtitle']

    def _lines(self, date_from, date_to, agent_id, provider_type, ho_id, customer_parent_id):
        query = "SELECT {} FROM {} WHERE {} ORDER BY {}".format(self._select(), self._from(provider_type), self._where(date_from, date_to, agent_id, provider_type, ho_id, customer_parent_id), self._order_by())

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _convert_data(self, lines):
        for i in lines:
            # i['date_invoice'] = self._datetime_user_context(i['date_invoice'])
            i['create_date'] = self._datetime_user_context(i['create_date'])
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _get_lines_data(self, date_from, date_to, agent_id, provider_type, ho_id, customer_parent_id):
        lines = []
        if provider_type != 'all':
            lines = self._lines(date_from, date_to, agent_id, provider_type, ho_id, customer_parent_id)
        else:
            provider_types = variables.PROVIDER_TYPE
            excluded = []
            for provider_type in provider_types:
                if provider_type not in excluded:
                    report_lines = self._lines(date_from, date_to, agent_id, provider_type, ho_id, customer_parent_id)
                    for j in report_lines:
                        lines.append(j)
        return lines

    def _prepare_valued(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        state = data_form['state']
        provider_type = data_form['provider_type']
        ho_id = data_form['ho_id']
        customer_parent_id = data_form['customer_parent_id']
        # line = self._get_lines_data(date_from, date_to, agent_id, provider_type, state)
        line = self._get_lines_data(date_from, date_to, agent_id, provider_type, ho_id, customer_parent_id)
        # line.sort(key=lambda x: x['invoice_id'])
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form,
            'provider_type': provider_type
        }
