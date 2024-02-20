from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)


class AgentReportRecapReservation(models.Model):
    _name = 'report.tt_agent_report_recap_reservation.agent_report_recap'
    _description = 'Recap Reservation'

    @staticmethod
    def _select():
        return """
        rsv.id, rsv.name as order_number, rsv.issued_date as issued_date, rsv.adult, rsv.child, rsv.infant, rsv.pnr,
        rsv.total as grand_total, rsv.total_commission, rsv.total_nta, rsv.provider_name as provider_name, 
        rsv.provider_alias as provider_alias, rsv.create_date, rsv.state,
        provider_type.name as provider_type, agent.name as agent_name, agent.email as agent_email,
        currency.name as currency_name,
        agent_type.name as agent_type_name,
        ledger.debit, ledger.credit, ledger_agent.name as ledger_agent_name, ledger.pnr as ledger_pnr, 
        ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider, 
        rsv.booker_insentif as commission_booker
        """

    @staticmethod
    def _select_join_service_charge():
        return """
        rsv.id, rsv.name as order_number, rsv.pnr, rsv.total as grand_total, rsv.total_commission, rsv.total_nta, rsv.state,
        booking_ids.id as booking_id, booking_ids.pnr as booking_pnr, booking_ids.state as booking_state,
        booking_service_charge.total as booking_charge_total, booking_service_charge.charge_type as booking_charge_type
        """

    @staticmethod
    def _select_join_channel_repricing():
        return """
            rsv.id, rsv.name as order_number, rsv.pnr, rsv.total as grand_total, rsv.total_commission, rsv.total_nta, rsv.state,
            passenger_ids.name as name, service_charges.charge_type as charge_type, service_charges.amount as service_charge_amount
            
            """
    #booking_ids.id as booking_id, booking_ids.pnr as booking_pnr, booking_ids.state as booking_state
    #booking_service_charge.total as booking_charge_total, booking_service_charge.charge_type as booking_charge_type

    @staticmethod
    def _from(provider_type):
        def selected_field(provider_type):
            if provider_type == 'airline':
                return 'booking_airline_id'
            elif provider_type == 'hotel':
                return 'resv_hotel_id'
            elif provider_type == 'tour':
                return 'booking_tour_id'
            elif provider_type == 'activity':
                return 'booking_activity_id'
            elif provider_type == 'visa':
                return 'visa_id'
            elif provider_type == 'passport':
                return 'passport_id'
            elif provider_type == 'cruise':
                return 'booking_cruise_id'
            else:
                return 'booking_offline_id'

        # query = """tt_ledger """
        query = """tt_reservation_""" + provider_type + """ rsv """
        query += """LEFT JOIN tt_agent agent ON rsv.agent_id = agent.id
        LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = rsv.agent_type_id
        LEFT JOIN res_currency currency ON currency.id = rsv.currency_id
        LEFT JOIN tt_ledger ledger ON ledger.res_model = rsv.res_model AND ledger.res_id = rsv.id
        LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
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
    def _where(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        where = """rsv.create_date >= '%s' and rsv.create_date <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        if state == 'issued':
            where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        elif state == 'booked':
            where += """ AND rsv.state IN ('partial_booked', 'booked')"""
        elif state == 'expired':
            where += """ AND rsv.state IN ('cancel2')"""
        elif state == 'issue-expired':
            where += """ AND rsv.state IN ('partial_issued', 'issued') OR rsv.state IN ('cancel2')"""
        elif state == 'others':
            where += """ AND rsv.state IN ('draft')"""
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
        # where += """ AND ledger.transaction_type = 3"""
        return where

    @staticmethod
    def _where_join_service_charge(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        where = """rsv.create_date >= '%s' and rsv.create_date <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        if state == 'issued':
            where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        elif state == 'booked':
            where += """ AND rsv.state IN ('partial_booked', 'booked')"""
        elif state == 'expired':
            where += """ AND rsv.state IN ('cancel2')"""
        elif state == 'issue-expired':
            where += """ AND rsv.state IN ('partial_issued', 'issued') OR rsv.state IN ('cancel2')"""
        elif state == 'others':
            where += """ AND rsv.state IN ('draft')"""
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
        # where += """ AND ledger.transaction_type = 3"""
        return where

    @staticmethod
    def _where_join_channel_repricing(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        where = """rsv.create_date >= '%s' and rsv.create_date <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        if state == 'issued':
            where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        elif state == 'booked':
            where += """ AND rsv.state IN ('partial_booked', 'booked')"""
        elif state == 'expired':
            where += """ AND rsv.state IN ('cancel2')"""
        elif state == 'issue-expired':
            where += """ AND rsv.state IN ('partial_issued', 'issued') OR rsv.state IN ('cancel2')"""
        elif state == 'others':
            where += """ AND rsv.state IN ('draft')"""
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
        # where += """ AND booking_service_charge.charge_type = 'CSC'"""
        # where += """ AND ledger.transaction_type = 3"""
        return where

    @staticmethod
    def _where_offline(date_from, date_to, agent_id, provider_type, state):
        where = """rsv.create_date >= '%s' and rsv.create_date <= '%s'""" % (date_from, date_to)
        if state and state != 'all':
            if state == 'issued':
                where += """ AND rsv.state IN ('paid', 'posted')"""
            elif state == 'booked':
                where += """ AND rsv.state IN ('sent')"""
            elif state == 'expired':
                where += """ AND rsv.state IN ('cancel2')"""
            elif state == 'others':
                where += """ AND rsv.state IN ('cancel', 'refund', 'draft', 'confirm')"""
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if provider_type != 'offline':
            where += """ AND rsv.provider_type = '%s' """ % provider_type
        return where

    @staticmethod
    def _group_by():
        # return 'rsv.name, rsv.create_date, rsv.state, rsv.provider_name, agent.name, tpt.id, agent_type.id , rsv.pnr , rsv.id , ssc.id , agent.id '
        # return 'rsv.id , ssc.id, agent.id, agent_type.id , tpt.id '
        return """booking_ids.id """

    @staticmethod
    def _order_by():
        return """
        rsv.create_date, rsv.name 
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

    def _lines(self, date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id):
        # SELECT
        query = 'SELECT ' + self._select()

        # FROM
        query += 'FROM ' + self._from(provider_type)

        # WHERE
        query += 'WHERE ' + self._where(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id)

        # GROUP BY & ORDER BY
        # query += 'GROUP BY ' + self._group_by()

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

    @staticmethod
    def _get_search(date_from, date_to, agent_id, state):
        line = []
        if state and state != 'all':
            line.append(('state', '=', state),)
        if agent_id:
            line.append(('agent_id', '=', agent_id),)
        line.append(('create_date', '<=', date_to),)
        line.append(('create_date', '>=', date_from),)
        return line

    @staticmethod
    def _get_service_charge(provider_type, booking_id):
        ssc = []
        if provider_type == 'airline':
            ssc.append(('booking_airline_id', '=', booking_id))
        elif provider_type == 'hotel':
            ssc.append(('resv_hotel_id', '=', booking_id))
        elif provider_type == 'tour':
            ssc.append(('booking_tour_id', '=', booking_id))
        elif provider_type == 'activity':
            ssc.append(('booking_activity_id', '=', booking_id))
        elif provider_type == 'visa':
            ssc.append(('visa_id', '=', booking_id))
        elif provider_type == 'passport':
            ssc.append(('passport_id', '=', booking_id))
        elif provider_type == 'offline':
            ssc.append(('booking_offline_id', '=', booking_id))
        return ssc

    def _lines_search(self, date_from, date_to, agent_id, provider_type, state):
        lines_env = self.env['tt.reservation.%s' % (provider_type)].search(self._get_search(date_from, date_to, agent_id, state), order='name asc')
        lines = []
        for line in lines_env:
            service_charge_env = self.env['tt.service.charge'].search(self._get_service_charge(provider_type, line.id))
            total = 0
            for ssc in service_charge_env:
                total += ssc.total
            lines.append({
                'create_date': line.create_date,
                'order_number': line.name,
                'agent_name': line.agent_id.name,
                'agent_type': line.agent_id.agent_type_id.name,
                'provider': line.provider_name,
                'total': total,
                'state': line.state,
                'provider_type': line.provider_type_id.name
            })
        return lines

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

    def _get_lines_data_search(self, date_from, date_to, agent_id, provider_type, state):
        lines = []
        if provider_type != 'all':
            lines = self._lines_search(date_from, date_to, agent_id, provider_type, state)
            lines = self._convert_data(lines, provider_type)
        else:
            # for i in range(500):
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines_search(date_from, date_to, agent_id, provider_type, state)
                report_lines = self._convert_data(report_lines, provider_type)
                for line in report_lines:
                    lines.append(line)
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
            rec['state'] = variables.BOOKING_STATE_STR[rec['state']] if rec['state'] else ''  # STATE_OFFLINE_STR[rec['state']]
        return lines

    def _convert_data_commission(self, lines, provider_type):
        for rec in lines:
            if rec['ledger_transaction_type'] == 3: #PADA LEDGER COMMISSION UPDATE DATA DEBIT DENGAN CREDIT
                rec['debit'] -= rec['credit']
        return lines

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Recap Reservation Report: ' + data_form['subtitle']

    def _prepare_values(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        ho_id = data_form['ho_id']
        customer_parent_id = data_form['customer_parent_id']
        state = data_form['state']
        provider_type = data_form['provider_type']
        currency_id = data_form.get('currency_id', '')
        # lines = self._get_lines_data_search(date_from, date_to, agent_id, provider_type, state)
        lines = self._get_lines_data(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id) #BOOKING
        second_lines = self._get_lines_data_join_service_charge(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id) #SERVICE CHARGE
        third_lines = self._get_lines_data_join_channel_repricing(date_from, date_to, agent_id, ho_id, customer_parent_id, provider_type, state, currency_id) #UPSELL
        self._report_title(data_form)

        return {
            'lines': lines,
            'second_lines': second_lines,
            'third_lines': third_lines,
            'data_form': data_form
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('data_form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        docs = self._prepare_values(data['data_form'])
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': docs
        }
