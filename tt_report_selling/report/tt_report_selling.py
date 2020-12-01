from odoo import models, fields, api, _
from ...tools import variables
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

class ReportSelling(models.Model):
    _name = 'report.tt_report_selling.report_selling'
    _description = "Selling Report"

    #to rule them all
    @staticmethod
    def _select():
        return """
        reservation.id as reservation_id, reservation.state as reservation_state, reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og, 
        reservation.carrier_name as carrier_name,
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.total as amount, provider_type.name as provider_type_name, 
        reservation.payment_method as reservation_payment_method,
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        agent.name as agent_name, agent_type.name as agent_type_name,
        provider.name as provider_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    @staticmethod
    def _select_invoice():
        return """
        COUNT(*), create_date as create_date_og
        """

    #only works with airline maybe train
    @staticmethod
    def _select_airline():
        return """
        reservation.id as reservation_id, 
        reservation.state as reservation_state,
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og,
        reservation.total as amount,
        reservation.carrier_name as carrier_name,
        reservation.sector_type as reservation_sector, 
        reservation.provider_name as reservation_provider_name, 
        reservation.direction as reservation_direction,
        reservation.booked_date as reservation_booked_date_og, 
        reservation.issued_date as reservation_issued_date_og,
        journey.id as journey_id,
        journey.departure_date as journey_departure_date,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        provider.name as provider_name,
        departure.display_name as departure, 
        destination.display_name as destination,
        COUNT(reservation_passenger.id) as reservation_passenger,
        agent.name as agent_name, agent_type.name as agent_type_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    @staticmethod
    def _select_train():
        return """
        reservation.id as reservation_id, 
        reservation.state as reservation_state,
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og,
        reservation.total as amount, 
        reservation.carrier_name as carrier_name,
        reservation.sector_type as reservation_sector, 
        reservation.provider_name as reservation_provider_name, 
        reservation.direction as reservation_direction,
        reservation.booked_date as reservation_booked_date_og, 
        reservation.issued_date as reservation_issued_date_og,
        journey.id as journey_id,
        journey.departure_date as journey_departure_date,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        provider.name as provider_name,
        departure.display_name as departure, destination.display_name as destination,
        COUNT(reservation_passenger.id) as reservation_passenger,
        agent.name as agent_name, agent_type.name as agent_type_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    @staticmethod
    def _select_hotel():
        return """
        reservation.id as reservation_id, 
        reservation.state as reservation_state, 
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        reservation.name as reservation_order_number, 
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.create_date as reservation_create_date_og, 
        reservation.nights as reservation_night, 
        reservation.provider_name as reservation_provider_name,
        reservation.total as amount, 
        reservation.carrier_name as carrier_name,
        reservation.hotel_name as reservation_hotel_name,
        reservation.hotel_city as hotel_city,
        reservation.hotel_city_id as hotel_city_id,
        country.name as country_name,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        provider.name as provider_name,
        COUNT(reservation_passenger.booking_id) as reservation_passenger,
        agent.name as agent_name, agent_type.name as agent_type_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    @staticmethod
    def _select_activity():
        return """
        reservation.id as reservation_id,
        reservation.state as reservation_state,
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        reservation.name as reservation_order_number,
        reservation.create_date as reservation_create_date_og,
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.total as amount,
        reservation.carrier_name as carrier_name,
        activity.name as reservation_activity_name,
        product.name as reservation_activity_product,
        activity_detail.visit_date as reservation_visit_date_og,
        activity_detail.timeslot as timeslot,
        reservation.elder as reservation_elder,
        reservation.adult as reservation_adult,
        reservation.child as reservation_child,
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        COUNT(reservation_passenger.booking_id) as reservation_passenger,
        agent.name as agent_name, agent_type.name as agent_type_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    @staticmethod
    def _select_tour():
        return """
        reservation.id as reservation_id, 
        reservation.state as reservation_state,
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og,
        reservation.booked_date as reservation_booked_date_og, 
        reservation.issued_date as reservation_issued_date_og,
        reservation.total as amount, 
        reservation.carrier_name as carrier_name,
        reservation.provider_name as reservation_provider_name, 
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        tour.name as tour_name,
        tour.tour_category as tour_category, 
        tour.tour_type as tour_type, 
        tour.tour_route as tour_route, 
        tour.duration as tour_duration, 
        country.name as tour_country_name,
        tour_location.country_name as tour_location_country,
        agent.name as agent_name, agent_type.name as agent_type_name,
        provider.name as provider_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    @staticmethod
    def _select_visa():
        return """
        reservation.id as reservation_id, 
        reservation.state as reservation_state,
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og,
        reservation.booked_date as reservation_booked_date_og, 
        reservation.issued_date as reservation_issued_date_og,
        reservation.total as amount, 
        reservation.carrier_name as carrier_name,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        provider.name as provider_name,
        country.name as country_name,
        COUNT(reservation_passenger.visa_id) as reservation_passenger,
        agent.name as agent_name, agent_type.name as agent_type_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    @staticmethod
    def _select_offline():
        return """
        reservation.id as reservation_id, 
        reservation.state as reservation_state,
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        reservation.name as reservation_order_number,
        reservation.create_date as reservation_create_date_og, 
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.confirm_date as reservation_confirm_date_og, 
        reservation.done_date as reservation_done_date_og,
        reservation.total as amount, 
        reservation.carrier_name as carrier_name,
        reservation.elder as reservation_elder,
        reservation.adult as reservation_adult,
        reservation.child as reservation_child,
        reservation.infant as reservation_infant,
        reservation.provider_name as reservation_provider_name,
        reservation.offline_provider_type as reservation_offline_provider_type, 
        reservation.nta_price as reservation_nta_price, 
        provider_type.name as provider_type_name,
        provider.name as provider_name,
        agent.name as agent_name, agent_type.name as agent_type_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    @staticmethod
    def _select_event():
        return """
        reservation.id as reservation_id, 
        reservation.state as reservation_state, 
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        reservation.name as reservation_order_number, 
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.create_date as reservation_create_date_og, 
        reservation.provider_name as reservation_provider_name,
        reservation.total as amount, 
        reservation.carrier_name as carrier_name,
        reservation.event_name as reservation_event_name,
        reservation.elder as reservation_elder, 
        reservation.adult as reservation_adult, 
        reservation.child as reservation_child, 
        reservation.infant as reservation_infant,
        provider_type.name as provider_type_name,
        provider.name as provider_name,
        COUNT(reservation_passenger.booking_id) as reservation_passenger,
        agent.name as agent_name, agent_type.name as agent_type_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    @staticmethod
    def _select_ppob():
        return """
        reservation.id as reservation_id, reservation.state as reservation_state, reservation.name as reservation_order_number, 
        reservation.create_date as reservation_create_date_og, 
        reservation.carrier_name as carrier_name,
        reservation.booked_date as reservation_booked_date_og,
        reservation.issued_date as reservation_issued_date_og,
        reservation.total as amount, provider_type.name as provider_type_name, 
        reservation.payment_method as reservation_payment_method,
        reservation.agent_id as agent_id, reservation.agent_type_id as agent_type_id,
        pro_ppob.carrier_name as carrier_name,
        provider_type.name as provider_type_name,
        provider.name as provider_name,
        agent.name as agent_name, agent_type.name as agent_type_name,
        ledger.id as ledger_id, ledger.ref as ledger_name,
        ledger.debit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, ledger_agent_type.name as ledger_agent_type_name,
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider
        """

    #for all
    @staticmethod
    def _from(provider_type):
        return """tt_reservation_""" + provider_type + """ reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_""" + provider_type + """ pro_type ON pro_type.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON pro_type.provider_id = provider.id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """

    @staticmethod
    def _from_invoice():
        return """tt_agent_invoice_line"""

    #only works for airline and train
    @staticmethod
    def _from_airline():
        return """tt_reservation_airline reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_destinations departure ON reservation.origin_id = departure.id
        LEFT JOIN tt_destinations destination ON reservation.destination_id = destination.id
        LEFT JOIN tt_journey_airline journey ON journey.booking_id = reservation.id
        LEFT JOIN tt_reservation_passenger_airline reservation_passenger ON reservation_passenger.booking_id = reservation.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_airline ON tt_provider_airline.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON tt_provider_airline.provider_id = provider.id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """

    @staticmethod
    def _from_train():
        return """tt_reservation_train reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_destinations departure ON reservation.origin_id = departure.id
        LEFT JOIN tt_destinations destination ON reservation.destination_id = destination.id
        LEFT JOIN tt_journey_train journey ON journey.booking_id = reservation.id
        LEFT JOIN tt_reservation_passenger_airline reservation_passenger ON reservation_passenger.booking_id = reservation.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_train pro_train ON pro_train.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON provider.id = pro_train.provider_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """

    @staticmethod
    def _from_hotel():
        return """tt_reservation_hotel reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_reservation_hotel_guest_rel reservation_passenger ON reservation_passenger.booking_id = reservation.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_hotel pro_hotel ON pro_hotel.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON provider.id = pro_hotel.provider_id
        LEFT JOIN res_city city ON city.id = reservation.hotel_city_id
        LEFT JOIN res_country country ON country.id = city.country_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """

    @staticmethod
    def _from_activity():
        return """tt_reservation_activity reservation
        LEFT JOIN tt_reservation_activity_details activity_detail ON activity_detail.booking_id = reservation.id
        LEFT JOIN tt_master_activity activity ON activity.id = activity_detail.activity_id
        LEFT JOIN tt_master_activity_lines product ON product.id = activity_detail.activity_product_id
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_reservation_passenger_activity reservation_passenger ON reservation_passenger.booking_id = reservation.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_activity pro_act ON pro_act.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON provider.id = pro_act.provider_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """

    @staticmethod
    def _from_tour():
        return """tt_reservation_tour reservation
        LEFT JOIN tt_master_tour tour ON tour.id = reservation.tour_id
        LEFT JOIN tt_tour_location_rel tour_location_rel ON tour_location_rel.product_id = tour.id
        LEFT JOIN tt_tour_master_locations tour_location ON tour_location.id = tour_location_rel.location_id
        LEFT JOIN res_country country ON tour_location.country_id = country.id
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_tour pro_tour ON pro_tour.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON provider.id = pro_tour.provider_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """

    @staticmethod
    def _from_visa():
        return """tt_reservation_visa reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN res_country country ON country.id = reservation.country_id
        LEFT JOIN tt_reservation_visa_order_passengers reservation_passenger ON reservation_passenger.visa_id = reservation.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_visa pro_visa ON pro_visa.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON provider.id = pro_visa.provider_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """

    @staticmethod
    def _from_event():
        return """tt_reservation_event reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_reservation_passenger_activity reservation_passenger ON reservation_passenger.booking_id = reservation.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_event pro_ev ON pro_ev.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON provider.id = pro_ev.provider_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """

    @staticmethod
    def _from_ppob():
        return """tt_reservation_ppob reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_reservation_passenger_activity reservation_passenger ON reservation_passenger.booking_id = reservation.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_ppob pro_ppob ON pro_ppob.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON provider.id = pro_ppob.provider_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """

    @staticmethod
    def _from_offline():
        return """tt_reservation_offline reservation
        LEFT JOIN tt_provider_type provider_type ON reservation.provider_type_id = provider_type.id
        LEFT JOIN tt_agent agent ON agent.id = reservation.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = reservation.agent_type_id
        LEFT JOIN tt_provider_offline pro_off ON pro_off.booking_id = reservation.id
        LEFT JOIN tt_provider provider ON provider.id = pro_off.provider_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = reservation.res_model AND ledger.res_id = reservation.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN tt_agent_Type ledger_agent_type ON ledger_agent_type.id = ledger.agent_type_id
        """
        # return """tt_reservation_offline"""

    # so far works with all
    @staticmethod
    def _group_by_airline():
        return """reservation.id, provider_type.name, departure.display_name, destination.display_name, journey.id, agent.name, agent_type.name, provider.name, ledger.id, ledger_agent.name, ledger_agent_type.name"""

    @staticmethod
    def _group_by_train():
        return """reservation.id, provider_type.name, departure.display_name, destination.display_name, journey.id, agent.name, agent_type.name, provider.name, ledger.id, ledger_agent.name, ledger_agent_type.name"""

    #specified hotel
    @staticmethod
    def _group_by_hotel():
        return """reservation.id, provider_type.name, agent.name, agent_type.name, provider.name, city.id, country.id, ledger.id, ledger_agent.name, ledger_agent_type.name"""

    @staticmethod
    def _group_by_activity():
        return """reservation.id, provider_type.name, agent.name, agent_type.name, provider.name, activity.name, product.name, activity_detail.visit_date, activity_detail.timeslot, ledger.id, ledger_agent.name, ledger_agent_type.name"""

    @staticmethod
    def _group_by_visa():
        return """reservation.id, country.name,  provider_type.name, agent.name, agent_type.name, provider.name, ledger.id, ledger_agent.name, ledger_agent_type.name"""

    @staticmethod
    def _group_by_tour():
        return """reservation.id, provider_type.name, agent.name, agent_type.name, provider.name, tour.name,
        tour.tour_category, 
        tour.tour_type, 
        tour.tour_route, 
        tour.duration, country.name,  tour_location.country_name, ledger.id, ledger_agent.name, ledger_agent_type.name """

    @staticmethod
    def _group_by_event():
        return """reservation.id, provider_type.name, agent.name, agent_type.name, provider.name, ledger.id, ledger_agent.name, ledger_agent_type.name"""

    @staticmethod
    def _group_by_ppob():
        return """reservation.id, provider_type.name, agent.name, agent_type.name, provider.name, pro_ppob.carrier_name, ledger.id, ledger_agent.name, ledger_agent_type.name"""

    #works with all
    @staticmethod
    def _where(date_from, date_to):
        where = """reservation.create_date >= '%s' and reservation.create_date <= '%s'""" % (date_from, date_to)
        return where

    # where invoice
    @staticmethod
    def _where_invoice(id):
        where = """res_id_resv = %s AND res_model_resv = 'tt.reservation.%s'""" % (id[0], id[1].lower())
        return where

    # where issued
    @staticmethod
    def _where_issued(date_from, date_to):
        where = """reservation.issued_date >= '%s' and reservation.issued_date <= '%s' AND reservation.state = 'issued' OR reservation.state = 'reissue'""" % (date_from, date_to)
        return where

    @staticmethod
    def _where_agent(agent_seq_id):
        where = """agent.seq_id = '%s'
        """ % (agent_seq_id)
        return where

    @staticmethod
    def _where_agent_type(agent_type_code):
        where = """agent_type.code = '%s'""" % (agent_type_code)
        return where

    @staticmethod
    def _where_provider(provider_code):
        where = """provider.code = '%s'""" % (provider_code)
        return where

    @staticmethod
    def _where_profit():
        # where = """ledger.transaction_type = 3 AND ledger.is_reversed = 'FALSE'"""
        where = """ ledger.is_reversed = 'FALSE'"""
        return where

    #works with all
    @staticmethod
    def _order_by():
        return """
        reservation.id
        """

    @staticmethod
    def _order_by_issued():
        return """
        reservation.issued_date
        """

    @staticmethod
    def _order_by_invoice():
        return """
        create_date
        """

    @staticmethod
    def _group_by_invoice():
        return """invoice_id, create_date"""

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Selling Report: ' + data_form['subtitle']

    def _lines(self, date_from, date_to, agent_seq_id, provider_type, provider_checker, context):
        if provider_checker == 'airline' or provider_checker == 'overall_airline':
            query = 'SELECT {} '.format(self._select_airline())
        elif provider_checker == 'train' or provider_checker == 'overall_train':
            query = 'SELECT {} '.format(self._select_train())
        elif provider_checker == 'hotel' or provider_checker == 'overall_hotel':
            query = 'SELECT {} '.format(self._select_hotel())
        elif provider_checker == 'activity' or provider_checker == 'overall_activity':
            query = 'SELECT {} '.format(self._select_activity())
        elif provider_checker == 'tour' or provider_checker == 'overall_tour':
            query = 'SELECT {} '.format(self._select_tour())
        elif provider_checker == 'visa' or provider_checker == 'overall_visa':
            query = 'SELECT {} '.format(self._select_visa())
        elif provider_checker == 'offline' or provider_checker == 'overall_offline':
            query = 'SELECT {} '.format(self._select_offline())
        elif provider_checker == 'event' or provider_checker == 'overall_event':
            query = 'SELECT {} '.format(self._select_event())
        elif provider_checker == 'ppob' or provider_checker == 'overall_ppob':
            query = 'SELECT {} '.format(self._select_ppob())
        elif provider_checker == 'invoice':
            query = 'SELECT {} '.format(self._select_invoice())
        else:
            query = 'SELECT {}'.format(self._select())

        if provider_checker == 'airline':
            query += 'FROM {} '.format(self._from_airline())
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_airline())
            query += 'ORDER BY {} '.format(self._order_by())
        elif provider_checker == 'train':
            query += 'FROM {} '.format(self._from_train())
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_train())
            query += 'ORDER BY {} '.format(self._order_by())
        elif provider_checker == 'hotel':
            query += 'FROM {} '.format(self._from_hotel())
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_hotel())
            query += 'ORDER BY {} '.format(self._order_by())
        elif provider_checker == 'activity':
            query += 'FROM {} '.format(self._from_activity())
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_activity())
            query += 'ORDER BY {} '.format(self._order_by())
        elif provider_checker == 'tour':
            query += 'FROM {} '.format(self._from_tour())
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_tour())
            query += 'ORDER BY {} '.format(self._order_by())
        elif provider_checker == 'visa':
            query += 'FROM {} '.format(self._from_visa())
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_visa())
            query += 'ORDER BY {} '.format(self._order_by())
        elif provider_checker == 'offline':
            query += 'FROM {} '.format(self._from_offline())
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'ORDER BY {} '.format(self._order_by())
        elif provider_checker == 'event':
            query += 'FROM {} '.format(self._from_event())
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_event())
            query += 'ORDER BY {} '.format(self._order_by())
        elif provider_checker == 'ppob':
            query += 'FROM {} '.format(self._from_ppob())
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_ppob())
            query += 'ORDER BY {} '.format(self._order_by())
        elif provider_checker == 'overall_airline':
            query += 'FROM {} '.format(self._from_airline())
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_airline())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'overall_activity':
            query += 'FROM {} '.format(self._from_activity())
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_activity())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'overall_event':
            query += 'FROM {} '.format(self._from_event())
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_event())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'overall_tour':
            query += 'FROM {} '.format(self._from_tour())
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'overall_train':
            query += 'FROM {} '.format(self._from_train())
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_train())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'overall_hotel':
            query += 'FROM {} '.format(self._from_hotel())
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_hotel())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'overall_visa':
            query += 'FROM {} '.format(self._from_visa())
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'GROUP BY {} '.format(self._group_by_visa())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'overall_offline':
            query += 'FROM {} '.format(self._from_offline())
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'overall_ppob':
            query += 'FROM {} '.format(self._from_ppob())
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'overall_passport':
            query += 'FROM {} '.format(self._from('passport'))
            query += 'WHERE {} AND {} '.format(self._where_issued(date_from, date_to), self._where_profit())
            if context['provider']:
                query += 'AND {} '.format(self._where_provider(context['provider']))
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'chanel_overall_airline':
            query += 'FROM {} '.format(self._from_airline())
            query += 'WHERE {} AND {} '.format(self._where_chanel(date_from, date_to), self._where_profit())
            query += 'GROUP BY {} '.format(self._group_by_airline())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'chanel_overall_activity':
            query += 'FROM {} '.format(self._from_activity())
            query += 'WHERE {} AND {} '.format(self._where_chanel(date_from, date_to), self._where_profit())
            query += 'GROUP BY {} '.format(self._group_by_activity())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'chanel_overall_event':
            query += 'FROM {} '.format(self._from_event())
            query += 'WHERE {} AND {} '.format(self._where_chanel(date_from, date_to), self._where_profit())
            query += 'GROUP BY {} '.format(self._group_by_event())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'chanel_overall_hotel':
            query += 'FROM {} '.format(self._from_hotel())
            query += 'WHERE {} AND {} '.format(self._where_chanel(date_from, date_to), self._where_profit())
            query += 'GROUP BY {} '.format(self._group_by_hotel())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'chanel_overall_tour':
            query += 'FROM {} '.format(self._from_tour())
            query += 'WHERE {} AND {} '.format(self._where_chanel(date_from, date_to), self._where_profit())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'chanel_overall_train':
            query += 'FROM {} '.format(self._from_train())
            query += 'WHERE {} AND {} '.format(self._where_chanel(date_from, date_to), self._where_profit())
            query += 'GROUP BY {} '.format(self._group_by_train())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'chanel_overall_visa':
            query += 'FROM {} '.format(self._from_visa())
            query += 'WHERE {} AND {} '.format(self._where_chanel(date_from, date_to), self._where_profit())
            query += 'GROUP BY {} '.format(self._group_by_visa())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'chanel_overall_offline':
            query += 'FROM {} '.format(self._from_offline())
            query += 'WHERE {} AND {} '.format(self._where_chanel(date_from, date_to), self._where_profit())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'chanel_overall_ppob':
            query += 'FROM {} '.format(self._from_ppob())
            query += 'WHERE {} AND {} '.format(self._where_chanel(date_from, date_to), self._where_profit())
            query += 'ORDER BY {} '.format(self._order_by_issued())
        elif provider_checker == 'invoice':
            query += 'FROM {} '.format(self._from_invoice())
            first_data = True
            for i in context['reservation']:
                if first_data:
                    query += 'WHERE {} '.format(self._where_invoice(i))
                    first_data = False
                else:
                    query += 'OR {} '.format(self._where_invoice(i))
            query += 'GROUP BY {} '.format(self._group_by_invoice())
            query += 'ORDER BY {} '.format(self._order_by_invoice())
        else:
            query += 'FROM {} '.format(self._from(provider_type))
            query += 'WHERE {} AND {} '.format(self._where(date_from, date_to), self._where_profit())
            if context['agent_type_code']:
                query += 'AND {} '.format(self._where_agent_type(context['agent_type_code']))
            if agent_seq_id:
                query += 'AND {} '.format(self._where_agent(agent_seq_id))
            query += 'ORDER BY {} '.format(self._order_by_issued())

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

    def _convert_data_ppob(self, lines):
        for i in lines:
            i['reservation_create_date'] = self._datetime_user_context(i['reservation_create_date_og'])
            if i['reservation_booked_date_og']:
                i['reservation_booked_date'] = self._datetime_user_context(i['reservation_booked_date_og'])
            if i['reservation_issued_date_og']:
                i['reservation_issued_date'] = self._datetime_user_context(i['reservation_issued_date_og'])
        return lines

    def _convert_data_invoice(self, lines):
        for i in lines:
            i['create_date'] = self._datetime_user_context(i['create_date_og'])
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

    def _get_lines_data(self, date_from, date_to, agent_id, provider_type, context = {}):
        if provider_type != 'all' and provider_type != 'overall':
            lines = self._lines(date_from, date_to, agent_id, provider_type, provider_type, context)
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
            elif provider_type == 'ppob':
                lines = self._convert_data_ppob(lines)
            elif provider_type == 'invoice':
                lines = self._convert_data_invoice(lines)
            else:
                lines = self._convert_data(lines)
            lines = self._seperate_data(lines)
        elif provider_type == 'overall':
            lines = []
            providers = variables.PROVIDER_TYPE
            for i in providers:
                # if i != 'activity':
                line = self._lines(date_from, date_to, agent_id, i, 'overall_' + i, context)
                # else:
                #     continue
                for j in line:
                    lines.append(j)
            lines = self._convert_data(lines)
            lines = self._seperate_data(lines)
        else:
            lines = []
            providers = variables.PROVIDER_TYPE
            for i in providers:
                # if i != 'activity':
                line = self._lines(date_from, date_to, agent_id, i, 'all', context)
                # else:
                #     continue
                for j in line:
                    lines.append(j)
            lines = self._convert_data(lines)
            lines = self._seperate_data(lines)
        return lines

    def _prepare_valued(self, data_form):
        # get data from form
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        agent_id = data_form['agent_id']
        provider_type = data_form['provider_type']
        # proceed data
        context = {
            'agent_seq_id': '',
            'agent_type_code': '',
            # 'provider_code': data['provider_code'],
            'reservation': '',
            'provider': ''
        }
        line = self._get_lines_data(date_from, date_to, agent_id, provider_type, context)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }

    def _get_reports(self, data):
    # get data from frontend
        date_from = data['start_date']
        date_to = data['end_date']
        # get agent data
        agent_id = data['agent_seq_id']
        agent_type = data['agent_type']
        # get provider
        provider = data['provider']

        if data['addons'] == 'book_issued':
            #for group we're gonna remove the overall prefix
            # check if data is not overall
            if data['type'] != 'overall':
                splits = data['type'].split("_")
                provider_type = splits[1]
            else:
                # if data is only overall then we're gonna change it to all
                provider_type = 'all'
        else:
            provider_type = data['type']
        reservation = []
        if provider_type == 'invoice':
            reservation = data['reservation']

        # proceed data
        context = {
            'agent_seq_id': agent_id,
            'agent_type_code': agent_type,
            # 'provider_code': data['provider_code'],
            'reservation': reservation,
            'provider': provider
        }
        line = self._get_lines_data(date_from, date_to, agent_id, provider_type, context)
        return {
            'lines': line
        }