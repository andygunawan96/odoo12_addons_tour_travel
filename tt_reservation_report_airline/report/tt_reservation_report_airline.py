from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util

import logging
_logger = logging.getLogger(__name__)

class ReservationReportAirline(models.Model):
    _name = 'report.tt_reservation_report_airline.reservation_rpt_airline'
    _description = 'Airline Report'

    @staticmethod
    def _select():
        # return """*"""
        return """
        airline.name as airline_number, 
        airline.pnr as airline_pnr, 
        airline.state as airline_state,
        airline.issued_date as airline_issued_date, 
        airline.adult as adult, 
        airline.child as child, 
        airline.infant as infant,
        airline.departure_date as departure_date, 
        airline.arrival_date as arrival_date,
        airline.sector_type as airline_sector, 
        airline.provider_name, 
        airline.carrier_name, 
        airline.total_fare,
        departure.display_name as departure_name, 
        departure.city as departure_city, 
        departure_country.name as departure_country,
        destination.display_name as destination_name, 
        destination.city as destination_city, 
        destination_country.name as destination_country,
        service_charge.charge_type, 
        service_charge.total as service_charge_total,
        booker.name as booker_name,
        currency.name as currency_name,
        COUNT(segment.id) as segment_counter
        """

    @staticmethod
    def _from():
        return """ tt_reservation_airline airline
        LEFT JOIN tt_destinations departure ON departure.id = airline.origin_id
        LEFT JOIN res_country departure_country ON departure_country.id = departure.country_id
        LEFT JOIN tt_destinations destination ON destination.id = airline.destination_id
        LEFT JOIN res_country destination_country ON destination_country.id = destination.country_id
        LEFT JOIN tt_service_charge service_charge ON service_charge.booking_airline_id = airline.id
        LEFT JOIN res_currency currency ON currency.id = airline.currency_id
        LEFT JOIN tt_customer booker ON booker.id = airline.booker_id
        LEFT JOIN tt_segment_airline segment ON segment.booking_id = airline.id
        """

    @staticmethod
    def _where(date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        where = """airline.create_date >= '%s' and airline.create_date <= '%s'""" % (date_from, date_to)
        if state == 'issue-expired':
            where += """ AND airline.state = 'issued' OR airline.state = 'cancel2'"""
        elif state != 'all':
            where += """ AND airline.state = '%s'""" %(state)

        if ho_id:
            where += """ AND airline.ho_id = """ + str(ho_id)
        if agent_id:
            where += """ AND airline.agent_id = """ + str(agent_id)
        if customer_parent_id:
            where += """ AND airline.customer_parent_id = """ + str(customer_parent_id)
        return where

    @staticmethod
    def _group_by():
        return """airline.id, departure.id, departure_country.id, destination.id, destination_country.id, service_charge.id, currency.id, booker.id
                """
    @staticmethod
    def _order_by():
        return """airline.id
        """

    def _lines(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        # query =  "SELECT {} FROM {}".format(self._select(), self._from())
        query = "SELECT {} FROM {} WHERE {} GROUP BY {} ORDER BY {}".format(self._select(), self._from(), self._where(date_from, date_to, agent_id, ho_id, customer_parent_id, state), self._group_by(), self._order_by())

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _get_lines_data(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state):
        lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, state)
        lines = self._convert_data(lines)
        return lines

    def _convert_data(self, lines):
        for i in lines:
            try:
                i['airline_issued_date'] = self._datetime_user_context(i['airline_issued_date'])
            except:
                pass
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%b-%d %H:%M:%S')

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Reservation Report Airline: ' + data_form['subtitle']

    def _prepare_valued(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        ho_id = data_form['ho_id']
        agent_id = data_form['agent_id']
        customer_parent_id = data_form['customer_parent_id']
        state = data_form['state']
        lines = self._get_lines_data(date_from, date_to, agent_id, ho_id, customer_parent_id, state)
        self._report_title(data_form)

        return {
            'lines': lines,
            'data_form': data_form
        }