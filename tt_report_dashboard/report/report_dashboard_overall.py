from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

#   this page consist of dependencies function for report by graph (frontend) a.k.a dashboard
#   do extend here if needed
class ReportDashboardOverall(models.Model):
    _name = 'report.tt_report_dashboard.overall'
    _description = 'Recap Reservation'

    ################
    #   All of select function to build SELECT function in SQL
    ################

    # select top up is a testing function in which we select how many top up in a day
    # but i didn't see this function as fit for report
    # so the function is not being use atm
    # but for reference and easy future proofing i'll leave it here
    @staticmethod
    def _select_top_up():
        return """
        topup.validated_amount
        """

    # select payment is a testing function to select reservation but group by payment method
    # not needed atm in report so the same reason as function above
    @staticmethod
    def _select_payment():
        return """ COUNT (payment_method)
        """
    # select join service is a function is needed for airline and overall (all provider type) report
    # since we need to separate the airline by the carrier itself not the reservation
    # hence we need to dive deep into the database where actual bill information is keep
    @staticmethod
    def _select_join_service_charge():
        return """
            rsv.id,
            rsv.name as order_number,
            rsv.pnr,
            rsv.total as grand_total,
            rsv.total_commission,
            rsv.total_nta,
            rsv.total_channel_upsell,
            rsv.state,
            booking_ids.id as booking_id,
            booking_ids.pnr as booking_pnr,
            booking_ids.state as booking_state,
            booking_service_charge.total as booking_charge_total,
            booking_service_charge.charge_type as booking_charge_type,
            booking_service_charge.is_ledger_created as ledger_created
            """

    ################
    #   All of FROM function to build FROM function in SQL
    #   name of the function correspond to respected SELECT functions for easy development
    ################

    @staticmethod
    def _from_top_up():
        return """
        tt_top_up topup
        """

    @staticmethod
    def _from_payment():
        return """ tt.reservation
        """

    @staticmethod
    def _from_join_service_charge(provider_type):
        query = """tt_reservation_""" + provider_type + """ rsv """
        # query += """LEFT JOIN tt_provider_""" + provider_type + """ booking_ids """
        query += """
            LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
            LEFT JOIN tt_provider_""" + provider_type + """ booking_ids ON booking_ids.booking_id = rsv.id
            LEFT JOIN tt_service_charge booking_service_charge ON booking_service_charge.provider_""" + provider_type + """_booking_id = booking_ids.id
            """
        return query

    ################
    #   All of WHERE function to build WHERE function in SQL
    #   name of the function correspond to respected SELECT, FORM functions for easy development
    ################

    @staticmethod
    def _where_top_up(start_date):
        return """
        topup.approve_date = '%s'
        """ % (start_date)

    @staticmethod
    def _where_payment(start_date, end_date):
        return """
        reservation.issued_date >= '%s' AND reservation.issued_date <= '%s' AND reservation.state == 'issued'
        """ % (start_date, end_date)

    @staticmethod
    def _where_join_service_charge(date_from, date_to, agent_id, provider_type):
        where = """rsv.issued_date >= '%s' and rsv.issued_date <= '%s'""" % (date_from, date_to)
        # if agent_id:
        #     where += """ AND rsv.agent_seq_id = '%s'""" % agent_id
        # if provider_type and provider_type != 'all':
        #     where += """ AND provider_type.code = '%s'""" % provider_type
        # where += """ AND ledger.is_reversed = 'FALSE'"""
        where += """ AND (rsv.state = 'issued' OR rsv.state = 'reissue')"""
        return where

    ################
    #   All of GROUP function to build GROUP BY function in SQL
    #   name of the function correspond to respected SELECT, FORM, WHERE functions for easy development
    ################

    @staticmethod
    def _group_by_payment():
        return """ payment_method
        """

    ################
    #   All of ORDER function to build ORDER BY function in SQL
    #   name of the function correspond to respected SELECT, FORM, WHERE, GROUP BY functions for easy development
    ################

    @staticmethod
    def _order_by_join_service_charge():
        return """
            rsv.create_date, rsv.name
            """

    ################
    #   Dependencies function for converting date to string, vice versa
    #
    ################

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime("%Y-%m-%d")

    def _convert_data(self, lines, provider_type):
        for rec in lines:
            rec['create_date'] = self._datetime_user_context(rec['create_date'])
            try:
                rec['issued_date'] = self._datetime_user_context(rec['issued_date'])
            except:
                pass
            # rec['state'] = variables.BOOKING_STATE_STR[rec['state']] if rec['state'] else ''  # STATE_OFFLINE_STR[rec['state']]
        return lines

    ################
    #   Function to build the dull query
    #   Within this function we will call the SELECT function, FROM function, WHERE function, etc
    #   for more information of what each query do, se explanation above every select function
    #   name of select function is the same as the _lines_[function name] or get_[function_name]
    ################

    # this function responsible to build and execute query to get service charge
    def _lines_join_service_charge(self, date_from, date_to, agent_id, provider_type):
        # SELECT
        query = 'SELECT ' + self._select_join_service_charge()

        # FROM
        query += 'FROM ' + self._from_join_service_charge(provider_type)

        # WHERE
        query += 'WHERE ' + self._where_join_service_charge(date_from, date_to, agent_id, provider_type)

        # ORDER BY
        query += 'ORDER BY ' + self._order_by_join_service_charge()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function responsible to build and execute query to get top up
    def get_top_up(self, start_date, end_date):
        query = "SELECT " + self._select_top_up() + "FROM " + self._from_top_up() + "WHERE " + self._where_top_up()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function responsible to build and execute query to get payment method report
    def get_payment_report(self, start_date, end_date):
        query = "SELECT " + self._selet_payment() + "FROM " + self._from_payment() + "WHERE " + self._where_payment(start_date, end_date) + "GROUP BY " + self._group_by_payment()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function responsible to build and execute query to get agent
    def get_agent_lines(self):
        query = "SELECT COALESCE(agent.seq_id, ''), agent.name, agent.agent_type_id FROM tt_agent agent ORDER BY name"

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function responsible to build and execute query to get agent type
    def get_agent_type_lines(self):
        query = "SELECT agent.name, agent.code ,agent.id FROM tt_agent_type agent ORDER BY name"

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function responsible to build and execute query to get provider
    def get_provider_lines(self):
        query = "SELECT provider.name, provider.code, provider_type.name as provider_type FROM tt_provider provider JOIN tt_provider_type provider_type ON provider.provider_type_id = provider_type.id ORDER BY name"

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function responsible to build and execute query to get carrier name
    # so far i do not see this function needed, because then the form would have to much interaction and less user friendly
    def get_carrier_lines(self):
        query = ""

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function responsible to build and execute query to get profit directly from ledger
    # this is an old function since the new function collect profit from reservation join directly to ledger
    # instead of splitting the function
    # because by joining the function will produce more accurate result
    def get_profit_lines(self, data):
        query = """
        SELECT ledger.date as date_og, ledger.debit, agent.name as agent_name, agent_type.name as agent_type, provider_type.name as provider_type
        FROM tt_ledger ledger
        LEFT JOIN tt_agent agent ON agent.id = ledger.agent_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = ledger.agent_type_id
        LEFT JOIN tt_provider_type provider_type ON provider_type.id = ledger.provider_type_id
        WHERE ledger.name LIKE 'Commission%' AND ledger.create_date >= '{}' AND ledger.create_date <= '{}' AND ledger.is_reversed = 'FALSE'
        """.format(data['start_date'], data['end_date'])

        if data['agent_type_seq_id']:
            query += """AND agent_type.code = '%s' """ % (data['agent_type_seq_id'])

        if data['agent_seq_id']:
            query += """AND agent.seq_id = '%s' """ % (data['agent_seq_id'])

        if data['provider_type']:
            query += """AND provider_type.code = '%s' """ % (data['provider_type'])

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function handle preparation to call query builder for service charge
    # it handles if we ask either all provider type or specified provider type
    def _get_lines_data_join_service_charge(self, date_from, date_to, agent_id, provider_type):
        lines = []
        if provider_type != 'all':
            # if we only ask for specific provider type
            lines = self._lines_join_service_charge(date_from, date_to, agent_id, provider_type)
        else:
            # if we ask for all provider type
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines_join_service_charge(date_from, date_to, agent_id, provider_type)
                for j in report_lines:
                    lines.append(j)
        return lines

    #   this is the function that gets call if we need to call one of the query in here
    #   set the correct type in data['search_type']
    def _get_reports(self, data):
        date_from = data['start_date']
        date_to = data['end_date']
        search_type = data['type']
        if search_type == 'top_up':
            # this will run function to get top up
            lines = self.get_top_up(date_from, date_to)
        elif search_type == 'payment':
            # this will run function to get payment method
            lines = self.get_payment_report(date_from, date_to)
        elif search_type == 'cash_report':
            # this function is not declared yet
            # and honestly i forget what this function is for :V
            # erase if need be
            lines = self.get_cash_report(date_from, date_to)

        # place for expansion~
        ##########################
        #   enter your code here
        ##########################

        else:
            lines = []
        return {
            'lines': lines
        }

    def _convert_data_profit(self, lines):
        for i in lines:
            i['date'] = self._datetime_user_context(i['date_og'])

            temp_booked_date = i['date'].split("-")
            i['year'] = temp_booked_date[0]
            i['month'] = temp_booked_date[1]
        return lines

    ##########################################
    #   this section contains handler function
    #   handler function is kind of a waiting room, for easier future proofing
    #   basically these functions call other function that actually do the work
    #   the catch is it is the function you call from other page or module or elsewhere
    #   it's like a get-set function in OOP
    ##########################################

    # get all agent
    # input - none
    # return [{'seq_id': xxx, 'name': 'John', 'agent_type_id': 'xx'}]
    def get_agent_all(self):
        lines = self.get_agent_lines()
        # lines.insert(0, {'seq_id': '', 'name': 'All', 'agent_type_id': ''})
        return lines

    # get all agent
    # input - none
    # return [{'seq_id': xxx, 'name': 'John'}]
    def get_agent_type_all(self):
        lines = self.get_agent_type_lines()
        return lines

    # get all agent
    # input - none
    # return [{'name': 'All Provider', 'code': '', 'provider_type': ''}]
    def get_provider_all(self):
        lines = self.get_provider_lines()
        # lines.insert(0, {'name': 'All Provider', 'code': '', 'provider_type': ''})
        return lines

    # get all agent
    # input - none
    # return list of dictionary
    def get_carrier(self):
        lines = self.get_carrier_lines()
        return lines

    # get all agent
    # input - required {'provider_type': [something], ...} (dictionary)
    # return [{'reservation': xxx, 'debit': n', ...}]
    def get_profit(self, data):
        # proceed something
        if data['provider_type'] != 'overall':
            provider = data['provider_type'].split("_")
            data['provider_type'] = provider[1]
        else:
            data['provider_type'] = ''

        lines = self.get_profit_lines(data)
        lines = self._convert_data_profit(lines)

        return lines

    # get all agent
    # input - data form from frontend (dictionary)
    # return [{'seq_id': xxx, 'name': 'John', 'agent_type_id': 'xx'}]
    def get_service_charge(self, data):
        date_from = data['start_date']
        date_to = data['end_date']
        # get agent data
        agent_id = data['agent_seq_id']
        agent_type = data['agent_type']
        # get provider
        if data['type'] != 'overall':
            splits = data['type'].split("_")
            provider_type = splits[1]
        else:
            # if data is only overall then we're gonna change it to all
            provider_type = 'all'

        # execute code
        lines = self._get_lines_data_join_service_charge(date_from, date_to, agent_id, provider_type)

        #return data
        return lines
