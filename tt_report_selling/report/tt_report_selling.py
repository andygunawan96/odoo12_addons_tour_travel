from odoo import models, fields, api, _
from ...tools import variables

import logging
_logger = logging.getLogger(__name__)

class ReportSelling(models.Model):
    _name = 'report.tt_report_selling.report_selling'
    _description = "Selling Report"

    #to rule them all
    @staticmethod
    def _select():
        return """
        reservation.id as reservation_id, reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og, reservation.state as reservation_state, 
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.total as amount, provider_type.name as provider_type_name, 
        reservation.payment_method as reservation_payment_method
        """

    #only works with airline maybe train
    @staticmethod
    def _select_airline():
        return """
        reservation.id as reservation_id, 
        reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og,
        reservation.total as amount, 
        reservation.sector_type as reservation_sector, 
        reservation.state as reservation_state,
        reservation.provider_name as reservation_provider_name, 
        reservation.direction as reservation_direction,
        reservation.booked_date as reservation_booked_date_og, 
        reservation.issued_date as reservation_issued_date_og,
        journey.departure_date as journey_departure_date,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        departure.display_name as departure, 
        destination.display_name as destination,
        COUNT(reservation_passenger.id) as reservation_passenger
        """

    @staticmethod
    def _select_train():
        return """
        reservation.id as reservation_id, 
        reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og,
        reservation.total as amount, 
        reservation.sector_type as reservation_sector, 
        reservation.state as reservation_state,
        reservation.provider_name as reservation_provider_name, 
        reservation.direction as reservation_direction,
        reservation.booked_date as reservation_booked_date_og, 
        reservation.issued_date as reservation_issued_date_og,
        journey.departure_date as journey_departure_date,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        departure.display_name as departure, destination.display_name as destination,
        COUNT(reservation_passenger.id) as reservation_passenger
        """

    @staticmethod
    def _select_hotel():
        return """
        reservation.id as reservation_id, 
        reservation.name as reservation_order_number, 
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.create_date as reservation_create_date_og, 
        reservation.nights as reservation_night, 
        reservation.provider_name as reservation_provider_name,
        reservation.total as amount, 
        reservation.state as reservation_state, 
        reservation.hotel_name as reservation_hotel_name,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        COUNT(reservation_passenger.booking_id) as reservation_passenger
        """

    @staticmethod
    def _select_activity():
        return """
        reservation.id as reservation_id, 
        reservation.name as reservation_order_number, 
        reservation.state as reservation_state,
        reservation.create_date as reservation_create_date_og, 
        reservation.booked_date as reservation_booked_date_og, 
        reservation.issued_date as reservation_issued_date_og,
        reservation.visit_date as reservation_visit_date_og, 
        reservation.total as amount, 
        reservation.activity_name as reservation_activity_name, 
        reservation.activity_product as reservation_activity_product,
        reservation.timeslot as reservation_timeslot,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        COUNT(reservation_passenger.booking_id) as reservation_passenger
        """

    @staticmethod
    def _select_tour():
        return """
        reservation.id as reservation_id, 
        reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og,
        reservation.booked_date as reservation_booked_date_og, 
        reservation.issued_date as reservation_issued_date_og,
        reservation.total as amount, 
        reservation.provider_name as reservation_provider_name, 
        reservation.state as reservation_state,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        tour.name as tour_name, 
        tour.tour_category as tour_category, 
        tour.tour_type as tour_type, 
        tour.tour_route as tour_route, 
        tour.duration as tour_duration, 
        country.name as tour_country_name,
        tour_location.country_name as tour_location_country
        """

    @staticmethod
    def _select_visa():
        return """
        reservation.id as reservation_id, 
        reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og,
        reservation.booked_date as reservation_booked_date_og, 
        reservation.issued_date as reservation_issued_date_og,
        reservation.total as amount, 
        reservation.state as reservation_state,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        country.name as country_name,
        COUNT(reservation_passenger.visa_id) as reservation_passenger
        """

    @staticmethod
    def _select_offline():
        return """
        reservation.id as reservation_id, 
        reservation.name as reservation_order_number,
        reservation.create_date as reservation_create_date_og, 
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.confirm_date as reservation_confirm_date_og, 
        reservation.done_date as reservation_done_date_og,
        reservation.total as amount, 
        reservation.elder as reservation_elder,
        reservation.adult as reservation_adult,
        reservation.child as reservation_child,
        reservation.infant as reservation_infant,
        reservation.provider_name as reservation_provider_name,
        reservation.state as reservation_state,
        reservation.offline_provider_type as reservation_offline_provider_type, 
        reservation.nta_price as reservation_nta_price, 
        reservation.vendor as reservation_vendor,
        provider_type.name as provider_type_name
        """

    @staticmethod
    def _select_event():
        return """
        reservation.id as reservation_id, 
        reservation.name as reservation_order_number, 
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.create_date as reservation_create_date_og, 
        reservation.nights as reservation_night, 
        reservation.provider_name as reservation_provider_name,
        reservation.total as amount, 
        reservation.state as reservation_state, 
        reservation.event_name as reservation_event_name,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        COUNT(reservation_passenger.booking_id) as reservation_passenger
        """

    #for all
    @staticmethod
    def _from(provider_type):
        return """tt_reservation_""" + provider_type + """ reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        """

    #only works for airline and train
    @staticmethod
    def _from_airline():
        return """tt_reservation_airline reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_destinations departure ON reservation.origin_id = departure.id
        LEFT JOIN tt_destinations destination ON reservation.destination_id = destination.id
        LEFT JOIN tt_journey_airline journey ON journey.booking_id = reservation.id
        LEFT JOIN tt_reservation_passenger_airline reservation_passenger ON reservation_passenger.booking_id = reservation.id
        """

    @staticmethod
    def _from_train():
        return """tt_reservation_train reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_destinations departure ON reservation.origin_id = departure.id
        LEFT JOIN tt_destinations destination ON reservation.destination_id = destination.id
        LEFT JOIN tt_journey_train journey ON journey.booking_id = reservation.id
        LEFT JOIN tt_reservation_passenger_airline reservation_passenger ON reservation_passenger.booking_id = reservation.id
        """

    @staticmethod
    def _from_hotel():
        return """tt_reservation_hotel reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_reservation_hotel_guest_rel reservation_passenger ON reservation_passenger.booking_id = reservation.id
        """

    @staticmethod
    def _from_activity():
        return """tt_reservation_activity reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_reservation_passenger_activity reservation_passenger ON reservation_passenger.booking_id = reservation.id
        """

    @staticmethod
    def _from_tour():
        return """tt_reservation_tour reservation
        LEFT JOIN tt_master_tour tour ON tour.id = reservation.tour_id
        LEFT JOIN tt_tour_location_rel tour_location_rel ON tour_location_rel.product_id = tour.id
        LEFT JOIN tt_tour_master_locations tour_location ON tour_location.id = tour_location_rel.location_id
        LEFT JOIN res_country country ON tour_location.country_id = country.id
        """

    @staticmethod
    def _from_visa():
        return """tt_reservation_visa reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN res_country country ON country.id = reservation.country_id
        LEFT JOIN tt_reservation_visa_order_passengers reservation_passenger ON reservation_passenger.visa_id = reservation.id
        """

    @staticmethod
    def _from_event():
        return """tt_reservation_event reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_reservation_passenger_activity reservation_passenger ON reservation_passenger.booking_id = reservation.id
        """

    @staticmethod
    def _from_offline():
        return """tt_reservation_offline reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        """
        # return """tt_reservation_offline"""

    # so far works with all
    @staticmethod
    def _group_by_airline():
        return """reservation.id, provider_type.name, departure.display_name, destination.display_name, journey.id"""

    @staticmethod
    def _group_by_train():
        return """reservation.id, provider_type.name, departure.display_name, destination.display_name, journey.id"""

    #specified hotel
    @staticmethod
    def _group_by_hotel():
        return """reservation.id, provider_type.name"""

    @staticmethod
    def _group_by_activity():
        return """reservation.id, provider_type.name"""

    @staticmethod
    def _group_by_visa():
        return """reservation.id, country.name"""

    @staticmethod
    def _group_by_event():
        return """reservation.id, provider_type.name"""

    #works with all
    @staticmethod
    def _where(date_from, date_to):
        where = """reservation.create_date >= '%s' and reservation.create_date <= '%s'""" % (date_from, date_to)
        return where

    #works with all
    @staticmethod
    def _order_by():
        return """
        reservation.id
        """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Selling Report: ' + data_form['subtitle']

    def _lines(self, date_from, date_to, agent_id, provider_type, provider_checker):
        if provider_checker == 'airline':
            query = 'SELECT {} '.format(self._select_airline())
        elif provider_checker == 'train':
            query = 'SELECT {} '.format(self._select_train())
        elif provider_checker == 'hotel':
            query = 'SELECT {} '.format(self._select_hotel())
        elif provider_checker == 'activity':
            query = 'SELECT {} '.format(self._select_activity())
        elif provider_checker == 'tour':
            query = 'SELECT {} '.format(self._select_tour())
        elif provider_checker == 'visa':
            query = 'SELECT {} '.format(self._select_visa())
        elif provider_checker == 'offline':
            query = 'SELECT {} '.format(self._select_offline())
        elif provider_checker == 'event':
            query = 'SELECT {} '.format(self._select_event())
        else:
            query = 'SELECT {}'.format(self._select())

        if provider_checker == 'airline':
            query += 'FROM {} '.format(self._from_airline())
            query += 'WHERE {} '.format(self._where(date_from, date_to))
            query += 'GROUP BY {} '.format(self._group_by_airline())
        elif provider_checker == 'train':
            query += 'FROM {} '.format(self._from_train())
            query += 'WHERE {} '.format(self._where(date_from, date_to))
            query += 'GROUP BY {} '.format(self._group_by_train())
        elif provider_checker == 'hotel':
            query += 'FROM {} '.format(self._from_hotel())
            query += 'WHERE {} '.format(self._where(date_from, date_to))
            query += 'GROUP BY {} '.format(self._group_by_hotel())
        elif provider_checker == 'activity':
            query += 'FROM {} '.format(self._from_activity())
            query += 'WHERE {} '.format(self._where(date_from, date_to))
            query += 'GROUP BY {} '.format(self._group_by_activity())
        elif provider_checker == 'tour':
            query += 'FROM {} '.format(self._from_tour())
            query += 'WHERE {} '.format(self._where(date_from, date_to))
        elif provider_checker == 'visa':
            query += 'FROM {} '.format(self._from_visa())
            query += 'WHERE {} '.format(self._where(date_from, date_to))
            query += 'GROUP BY {} '.format(self._group_by_visa())
        elif provider_checker == 'offline':
            query += 'FROM {} '.format(self._from_offline())
            query += 'WHERE {} '.format(self._where(date_from, date_to))
        elif provider_checker == 'event':
            query += 'FROM {} '.format(self._from_event())
            query += 'WHERE {} '.format(self._where(date_from, date_to))
            query += 'GROUP BY {} '.format(self._group_by_event())
        else:
            query += 'FROM {} '.format(self._from(provider_type))
            query += 'WHERE {} '.format(self._where(date_from, date_to))

        query += 'ORDER BY {} '.format(self._order_by())

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # ============ convert for all ======================
    def _convert_data(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])
        return lines

    def _convert_data_hotel(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])
        return lines

    def _convert_data_airline(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])
        return lines

    def _convert_data_tour(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])
        return lines

    def _convert_data_train(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])

        return lines

    def _convert_data_activity(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])
            if i['reservation_visit_date_og']:
                i['reservation_visit_date'] = self._datetime_user_context(i['reservation_visit_date_og'])
        return lines

    def _convert_data_visa(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])
        return lines

    def _convert_data_offline(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])
            if i['reservation_confirm_date_og']:
                i['reservation_confirm_date'] = self._datetime_user_context(i['reservation_confirm_date_og'])
            if i['reservation_done_date_og']:
                i['reservation_done_date'] = self._datetime_user_context(i['reservation_done_date_og'])

        return lines

    def _convert_data_event(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])
        return lines

    def _seperate_data(self, lines):
        for i in lines:
            try:
                temp_booked_date = i['reservation_booked_date'].split("-")
                i['booked_year'] = temp_booked_date[0]
                i['booked_month'] = temp_booked_date[1]
            except:
                pass
            try:
                temp_issued_date = i['reservation_issued_date'].split("-")
                i['issued_year'] = temp_issued_date[0]
                i['issued_month'] = temp_issued_date[1]
            except:
                pass
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime("%Y-%m-%d")

    def _get_lines_data(self, date_from, date_to, agent_id, provider_type):
        if provider_type != 'all':
            lines = self._lines(date_from, date_to, agent_id, provider_type, provider_type)
            if provider_type == 'airline':
                lines = self._convert_data_airline(lines)
            elif provider_type == 'train':
                lines = self._convert_data_train(lines)
            elif provider_type == 'tour':
                lines = self._convert_data_tour(lines)
            elif provider_type == 'hotel':
                lines = self._convert_data_hotel(lines)
            elif provider_type == 'activity':
                lines = self._convert_data_activity(lines)
            elif provider_type == 'visa':
                lines = self._convert_data_visa(lines)
            elif provider_type == 'offline':
                lines = self._convert_data_offline(lines)
            elif provider_type == 'event':
                lines = self._convert_data_event(lines)
            else:
                lines = self._convert_data(lines)
            lines = self._seperate_data(lines)
        else:
            lines = []
            providers = variables.PROVIDER_TYPE
            for i in providers:
                line = self._lines(date_from, date_to, agent_id, i, 'all')
                for j in line:
                    lines.append(j)
            lines = self._convert_data(lines)
            lines = self._seperate_data(lines)
        return lines

    def _prepare_valued(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        agent_id = data_form['agent_id']
        provider_type = data_form['provider_type']
        line = self._get_lines_data(date_from, date_to, agent_id, provider_type)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }

    def _get_reports(self, data):
        date_from = data['start_date']
        date_to = data['end_date']
        provider_type = data['type']
        if provider_type == 'overall':
            provider_type = 'all'
        agent_id = ''
        line = self._get_lines_data(date_from, date_to, agent_id, provider_type)
        return {
            'lines': line
        }