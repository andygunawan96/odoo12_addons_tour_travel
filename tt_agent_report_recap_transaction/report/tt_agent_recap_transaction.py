from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class AgentReportRecapTransacion(models.Model):
    _name = 'report.tt_agent_report_recap_transaction.agent_report_recap'
    _description = 'Recap Transaction'

    ################
    #   All of select function to build SELECT function in SQL
    ################

    # this select function responsible to build query to produce the neccessary report
    @staticmethod
    def _select():
        return """
            rsv.id, rsv.name as order_number, rsv.state, creates.id as creator_id, creates_partner.name as create_by, 
            issued.id as issued_uid, issued_partner.name as issued_by, rsv.issued_date as issued_date, rsv.adult, rsv.child, rsv.infant, rsv.pnr,
            rsv.total as grand_total, rsv.total_commission, rsv.total_nta, rsv.provider_name, rsv.create_date,
            provider_type.code as provider_type_code, provider_type.name as provider_type, agent.name as agent_name, agent.email as agent_email,
            currency.name as currency_name, rsv.carrier_name as carrier_name, customer_parent.name as customer_parent_name, 
            customer_parent_type.name as customer_parent_type_name, provider_booking.pnr as provider_pnr,
            agent_type.name as agent_type_name, ledger.id as ledger_id, ledger.ref as ledger_name,
            ledger.debit, ledger.credit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr,
            ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider,
            ledger.description as ledger_description, rsv.booker_insentif as commission_booker
            """

    @staticmethod
    def _sel_direction():
        return """
            ,rsv.direction as direction, rsv.sector_type as sector_type, rsv.departure_date as departure_date, rsv.arrival_date as arrival_date,
            origin_obj.display_name as origin, dest_obj.display_name as destination
            """

    @staticmethod
    def _sel_train_name():
        return """
                ,rsv.train_name as product_desc
                """

    @staticmethod
    def _sel_room_night():
        return """
            ,rsv.nights as nights, rsv.room_count as room_count, rsv.checkin_date as departure_date, rsv.checkout_date as arrival_date, 
            rsv.hotel_name as product_desc, rsv.hotel_city as destination
            """

    @staticmethod
    def _offline():
        return """
        ,rsv.offline_provider_type as offline_provider
        """

    # this select function responsible build query for service charge
    @staticmethod
    def _select_join_service_charge():
        return """
            rsv.id, rsv.name as order_number, rsv.pnr, rsv.total as grand_total, rsv.total_commission, rsv.total_nta, rsv.state,
            booking_ids.id as booking_id, booking_ids.pnr as booking_pnr, booking_ids.state as booking_state,
            booking_service_charge.total as booking_charge_total, booking_service_charge.charge_type as booking_charge_type,
            booking_service_charge.charge_code as booking_charge_code, booking_service_charge.is_ledger_created as ledger_created
            """

    @staticmethod
    def _select_join_channel_repricing():
        return """
                rsv.id, rsv.name as order_number, rsv.pnr, rsv.total as grand_total, rsv.total_commission, rsv.total_nta, rsv.state, 
                passenger_ids.title as psg_title, passenger_ids.name as name, service_charges.charge_type as charge_type, 
                service_charges.amount as service_charge_amount
                """

    @staticmethod
    def _select_join_psg_ticket():
        return """
                rsv.id, rsv.name as order_number, rsv.pnr, rsv.total as grand_total, rsv.total_commission, rsv.total_nta, rsv.state, 
                pax_obj.id as psg_id, pax_obj.title as psg_title, pax_obj.name as psg_name, pax_obj.description as psg_free_text, 
                provider_booking.pnr as provider_pnr
                """

    @staticmethod
    def _sel_ticket_number():
        return """
                ,ticket_obj.ticket_number as ticket_number
                """

    ################
    #   All of FROM function to build FROM function in SQL
    #   name of the function correspond to respected SELECT functions for easy development
    ################
    @staticmethod
    def _from(provider_type):
        # query = """tt_ledger """
        model_name = 'tt.reservation.' + provider_type
        query = """tt_reservation_""" + provider_type + """ rsv """
        query += """LEFT JOIN tt_agent agent ON rsv.agent_id = agent.id
        LEFT JOIN tt_provider_""" + provider_type + """ provider_booking ON provider_booking.booking_id = rsv.id
        LEFT JOIN tt_customer_parent customer_parent ON rsv.customer_parent_id = customer_parent.id
        LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
        LEFT JOIN tt_customer_parent_type customer_parent_type ON customer_parent_type.id = rsv.customer_parent_type_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = rsv.agent_type_id
        LEFT JOIN res_currency currency ON currency.id = rsv.currency_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = '""" + model_name + """' AND ledger.res_id = rsv.id AND ledger.pnr = provider_booking.pnr AND ledger.is_reversed = 'FALSE' 
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN res_users creates ON creates.id = rsv.user_id
        LEFT JOIN res_partner creates_partner ON creates.partner_id = creates_partner.id
        LEFT JOIN res_users issued ON issued.id = rsv.issued_uid
        LEFT JOIN res_partner issued_partner ON issued.partner_id = issued_partner.id
        """
        if provider_type in ['airline', 'train', 'bus']:
            query += """
            LEFT JOIN tt_destinations origin_obj on rsv.origin_id = origin_obj.id
            LEFT JOIN tt_destinations dest_obj on rsv.destination_id = dest_obj.id
            """
        return query

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

    @staticmethod
    def _from_join_channel_repricing(provider_type):
        query = """tt_reservation_""" + provider_type + """ rsv """
        # query += """LEFT JOIN tt_provider_""" + provider_type + """ booking_ids """
        query += """
                LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id"""
        if provider_type == 'visa':
            query += """
                            LEFT JOIN tt_reservation_visa_order_passengers passenger_ids ON passenger_ids.visa_id = rsv.id
                            """
        elif provider_type == 'offline':
            query += """
                            LEFT JOIN tt_reservation_offline_passenger passenger_ids ON passenger_ids.booking_id = rsv.id
                            """
        elif provider_type == 'passport':
            query += """
                            LEFT JOIN tt_reservation_passport_order_passengers passenger_ids ON passenger_ids.passport_id = rsv.id
                            """
        else:
            query += """
                LEFT JOIN tt_reservation_passenger_""" + provider_type + """ passenger_ids ON passenger_ids.booking_id = rsv.id
                """

        query += """
                LEFT JOIN tt_reservation_""" + provider_type + """_channel_charge_rel scs_rel ON scs_rel.passenger_id = passenger_ids.id
                LEFT JOIN tt_service_charge service_charges ON scs_rel.service_charge_id = service_charges.id
               """
        # LEFT JOIN tt_service_charge booking_service_charge ON booking_service_charge.tt_reservation_""" + provider_type + """_cost_charge_rel = scs_rel.id
        return query

    @staticmethod
    def _from_join_psg_ticket(provider_type):
        query = """tt_reservation_""" + provider_type + """ rsv """
        query += """
            LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
            LEFT JOIN tt_provider_""" + provider_type + """ provider_booking ON provider_booking.booking_id = rsv.id
            LEFT JOIN tt_ticket_""" + provider_type + """ ticket_obj ON ticket_obj.provider_id = provider_booking.id
            LEFT JOIN tt_reservation_passenger_""" + provider_type + """ pax_obj ON pax_obj.id = ticket_obj.passenger_id
            """
        return query

    @staticmethod
    def _from_join_psg_no_ticket(provider_type):
        query = """tt_reservation_""" + provider_type + """ rsv """
        query += """
            LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
            LEFT JOIN tt_provider_""" + provider_type + """ provider_booking ON provider_booking.booking_id = rsv.id
            """
        if provider_type == 'visa':
            query += """
                LEFT JOIN tt_reservation_visa_order_passengers pax_obj ON pax_obj.visa_id = rsv.id
                """
        elif provider_type == 'offline':
            query += """
                LEFT JOIN tt_reservation_offline_passenger pax_obj ON pax_obj.booking_id = rsv.id
                """
        elif provider_type == 'passport':
            query += """
                LEFT JOIN tt_reservation_passport_order_passengers pax_obj ON pax_obj.passport_id = rsv.id
                """
        else:
            query += """
                LEFT JOIN tt_reservation_passenger_""" + provider_type + """ pax_obj ON pax_obj.booking_id = rsv.id
                """
        return query

    ################
    #   All of WHERE function to build WHERE function in SQL
    #   name of the function correspond to respected SELECT, FORM functions for easy development
    ################
    @staticmethod
    def _where(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        where = """rsv.issued_date >= '%s' and rsv.issued_date <= '%s'""" % (date_from, date_to)
        if ho_id:
            where += """ AND rsv.ho_id = %s """ % ho_id
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if customer_parent_id:
            where += """ AND rsv.customer_parent_id = %s""" % customer_parent_id
        if currency_id:
            where += """ AND rsv.currency_id = %s""" % currency_id
        if provider_type and provider_type != 'all':
            where += """ AND provider_type.code = '%s' """ % provider_type
        if state == 'issued':
            where += """ AND (rsv.state = '%s' OR rsv.state = 'reissue') """ % state
        elif state == 'refund':
            where += """ AND (rsv.state = '%s') """ % state
        elif state == 'issued_refund':
            where += """ AND (rsv.state = 'issued' OR rsv.state = 'refund' OR rsv.state = 'reissue') """
        return where

    @staticmethod
    def _where_join_service_charge(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        where = """rsv.issued_date >= '%s' and rsv.issued_date <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        # where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        if ho_id:
            where += """ AND rsv.ho_id = %s """ % ho_id
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if customer_parent_id:
            where += """ AND rsv.customer_parent_id = %s""" % customer_parent_id
        if currency_id:
            where += """ AND rsv.currency_id = %s""" % currency_id
        if provider_type and provider_type != 'all':
            where += """ AND provider_type.code = '%s'""" % provider_type
        # where += """ AND ledger.is_reversed = 'FALSE'"""
        if state == 'issued':
            where += """ AND (rsv.state = '%s' OR rsv.state = 'reissue') """ % state
        elif state == 'refund':
            where += """ AND (rsv.state = '%s') """ % state
        elif state == 'issued_refund':
            where += """ AND (rsv.state = 'issued' OR rsv.state = 'refund' OR rsv.state = 'reissue') """
        return where

    @staticmethod
    def _where_join_channel_repricing(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        where = """rsv.issued_date >= '%s' and rsv.issued_date <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        # where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        if ho_id:
            where += """ AND rsv.ho_id = %s """ % ho_id
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if customer_parent_id:
            where += """ AND rsv.customer_parent_id = %s""" % customer_parent_id
        if currency_id:
            where += """ AND rsv.currency_id = %s""" % currency_id
        if provider_type and provider_type != 'all':
            where += """ AND provider_type.code = '%s'""" % provider_type
        # where += """ AND ledger.is_reversed = 'FALSE'"""
        if state == 'issued':
            where += """ AND (rsv.state = '%s' OR rsv.state = 'reissue') """ % state
        elif state == 'refund':
            where += """ AND (rsv.state = '%s') """ % state
        elif state == 'issued_refund':
            where += """ AND (rsv.state = 'issued' OR rsv.state = 'refund' OR rsv.state = 'reissue') """
        return where

    @staticmethod
    def _where_join_psg_ticket(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        where = """rsv.issued_date >= '%s' and rsv.issued_date <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        # where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        if ho_id:
            where += """ AND rsv.ho_id = %s """ % ho_id
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if customer_parent_id:
            where += """ AND rsv.customer_parent_id = %s""" % customer_parent_id
        if currency_id:
            where += """ AND rsv.currency_id = %s""" % currency_id
        if provider_type and provider_type != 'all':
            where += """ AND provider_type.code = '%s'""" % provider_type
        # where += """ AND ledger.is_reversed = 'FALSE'"""
        if state == 'issued':
            where += """ AND (rsv.state = '%s' OR rsv.state = 'reissue') """ % state
        elif state == 'refund':
            where += """ AND (rsv.state = '%s') """ % state
        elif state == 'issued_refund':
            where += """ AND (rsv.state = 'issued' OR rsv.state = 'refund' OR rsv.state = 'reissue') """
        return where

    ################
    #   All of ORDER function to build ORDER BY function in SQL
    #   name of the function correspond to respected SELECT, FORM, WHERE, GROUP BY functions for easy development
    ################
    @staticmethod
    def _order_by():
        return """
        rsv.create_date, rsv.name, ledger.id 
        """
    @staticmethod
    def _order_by_join_service_charge():
        return """
        rsv.create_date, rsv.name
        """

    @staticmethod
    def _order_by_join_channel_repricing():
        return """
                rsv.create_date, rsv.name
                """

    @staticmethod
    def _order_by_join_psg_ticket():
        return """
                    rsv.create_date, rsv.name
                    """

    ################
    #   Function to build the full query
    #   Within this function we will call the SELECT function, FROM function, WHERE function, etc
    #   for more information of what each query do, se explanation above every select function
    #   name of select function is the same as the _lines_[function name] or get_[function_name]
    ################
    def _lines(self, date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        # SELECT
        query = 'SELECT ' + self._select()
        if provider_type in ['airline', 'train', 'bus']:
            query += self._sel_direction()
            if provider_type == 'train':
                query += self._sel_train_name()
        if provider_type == 'hotel':
            query += self._sel_room_night()
        if provider_type == 'offline':
            query += self._offline()

        # FROM
        query += 'FROM ' + self._from(provider_type)

        # WHERE
        query += 'WHERE ' + self._where(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)

        # 'GROUP BY' + self._group_by() + \
        query += 'ORDER BY ' + self._order_by()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _lines_join_service_charge(self, date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        # SELECT
        query = 'SELECT ' + self._select_join_service_charge()

        # FROM
        query += 'FROM ' + self._from_join_service_charge(provider_type)

        # WHERE
        query += 'WHERE ' + self._where_join_service_charge(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)

        # ORDER BY
        query += 'ORDER BY ' + self._order_by_join_service_charge()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _lines_join_channel_repricing(self, date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        # SELECT
        query = 'SELECT ' + self._select_join_channel_repricing()

        # FROM
        query += 'FROM ' + self._from_join_channel_repricing(provider_type)

        # WHERE
        query += 'WHERE ' + self._where_join_channel_repricing(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)

        # ORDER BY
        query += 'ORDER BY ' + self._order_by_join_channel_repricing()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _lines_join_psg_ticket(self, date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        # SELECT
        query = 'SELECT ' + self._select_join_psg_ticket()
        if provider_type in ['airline', 'train']:
            query += self._sel_ticket_number()
            # FROM
            query += 'FROM ' + self._from_join_psg_ticket(provider_type)
        else:
            # FROM
            query += 'FROM ' + self._from_join_psg_no_ticket(provider_type)

        # WHERE
        query += 'WHERE ' + self._where_join_psg_ticket(date_from, date_to, agent_id, ho_id, customer_parent_id,
                                                               provider_type, state, currency_id)

        # ORDER BY
        query += 'ORDER BY ' + self._order_by_join_psg_ticket()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function handle preparation to call query builder for service charge
    def _get_lines_data(self, date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        lines = []
        if provider_type != 'all':
            lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)
            lines = self._convert_data(lines, provider_type)
        else:
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)
                report_lines = self._convert_data(report_lines, provider_type)
                report_lines = self._convert_data_commission(report_lines, provider_type)
                for line in report_lines:
                    lines.append(line)
        return lines

    # this function handle preparation to call query builder for service charge
    def _get_lines_data_join_service_charge(self, date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        lines = []
        if provider_type != 'all':
            lines = self._lines_join_service_charge(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)
        else:
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines_join_service_charge(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)
                for j in report_lines:
                    lines.append(j)
        return lines

    def _get_lines_data_join_channel_repricing(self, date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        lines = []
        if provider_type != 'all':
            lines = self._lines_join_channel_repricing(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)
        else:
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines_join_channel_repricing(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)
                for j in report_lines:
                    lines.append(j)
        return lines

    def _get_lines_data_join_psg_ticket(self, date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        lines = []
        if provider_type != 'all':
            lines = self._lines_join_psg_ticket(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)
        else:
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines_join_psg_ticket(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)
                for j in report_lines:
                    lines.append(j)
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _convert_data(self, lines, provider_type):
        for rec in lines:
            rec['create_date'] = self._datetime_user_context(rec['create_date'])
            try:
                rec['issued_date'] = self._datetime_user_context(rec['issued_date'])
            except:
                pass
            # rec['state'] = variables.BOOKING_STATE_STR[rec['state']] if rec['state'] else ''  # STATE_OFFLINE_STR[rec['state']]
        return lines

    def _convert_data_commission(self, lines, provider_type):
        for rec in lines:
            if rec['ledger_transaction_type'] == 3: #HITUNG CREDIT PADA LEDGER TYPE COMMISSION
                rec['debit'] -= rec['credit']
        return lines


    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Recap Transaction Report: ' + data_form['subtitle']

    def _prepare_values(self, data_form):
        data_form['is_ho'] = (self.env.user.has_group('tt_base.group_tt_tour_travel') and self.env.user.agent_id.is_ho_agent) or self.env.user.has_group('base.group_erp_manager')
        if self.env.user.has_group('tt_base.group_tt_corpor_user'):
            data_form['is_corpor'] = True
        ho_obj = False
        if data_form.get('ho_id'):
            ho_obj = self.env['tt.agent'].sudo().browse(int(data_form['ho_id']))
        if not ho_obj:
            ho_obj = self.env.user.agent_id.ho_id
        data_form['ho_name'] = ho_obj and ho_obj.name or self.env.ref('tt_base.rodex_ho').sudo().name
        data_form['is_pricing_breakdown'] = ho_obj and ho_obj.pricing_breakdown or False
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        # if not data_form['state']:
        #     data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        ho_id = data_form['ho_id']
        customer_parent_id = data_form['customer_parent_id']
        state = data_form['state']
        provider_type = data_form['provider_type']
        currency_id = data_form.get('currency_id', '')
        lines = self._get_lines_data(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id) #BOOKING
        second_lines = self._get_lines_data_join_service_charge(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id) # SERVICE CHARGE
        third_lines = self._get_lines_data_join_channel_repricing(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)  # UPSELL
        fourth_lines = self._get_lines_data_join_psg_ticket(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id) # passengers and tickets
        self._report_title(data_form)

        return {
            'lines': lines,
            'second_lines': second_lines,
            'third_lines': third_lines,
            'fourth_lines': fourth_lines,
            'data_form': data_form
        }
