from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class MedicalVendorReportRecapTransacion(models.Model):
    _name = 'report.tt_report_recap_transaction.medical_vendor'
    _description = 'Recap Transaction'

    ################
    #   All of select function to build SELECT function in SQL
    ################

    # this select function responsible build query for passengers
    @staticmethod
    def _select():
        return """
            rsv.id as rsv_id, rsv.name as order_number, rsv.state as state, rsv.adult as adult, rsv.state_vendor as state_vendor, 
            rsv.provider_name as provider_name, provider_type.name as provider_type, carrier.name as carrier_name, 
            rsv.issued_date as issued_date, psg.verified_date as verified_date, timeslot.datetimeslot as test_datetime, 
            usr_partner.name as verified_uid, psg.booking_id as booking_id, psg.title as title, COALESCE(psg.seq_id, '') as psg_seq_id,
            psg.first_name as first_name, psg.last_name as last_name, psg.birth_date as birth_date, 
            psg.ticket_number as ticket_number, psg.identity_number as identity_number, psg.address_ktp as address_ktp
            """

    @staticmethod
    def _from(provider_type):
        query = """tt_reservation_passenger_""" + provider_type + """ psg """
        query += """LEFT JOIN tt_reservation_""" + provider_type + """ rsv ON rsv.id = psg.booking_id """
        query += """LEFT JOIN tt_agent agent ON rsv.agent_id = agent.id
                LEFT JOIN res_users usr ON usr.id = psg.verified_uid
                LEFT JOIN res_partner usr_partner ON usr_partner.id = usr.partner_id
                LEFT JOIN tt_provider_type provider_type ON provider_type.id = rsv.provider_type_id
                LEFT JOIN tt_transport_carrier carrier ON carrier.code = rsv.carrier_name
                """
        query += """LEFT JOIN tt_timeslot_""" + provider_type + """ timeslot ON timeslot.id = rsv.picked_timeslot_id """
        return query

    @staticmethod
    def _where(period_mode, date_from, date_to, agent_id, provider_type, state, state_vendor):
        if period_mode == 'issued_date':
            where = """rsv.issued_date >= '%s' and rsv.issued_date <= '%s'""" % (date_from, date_to)
        elif period_mode == 'verified_date':
            where = """psg.verified_date >= '%s' and psg.verified_date <= '%s'""" % (date_from, date_to)
        else:
            where = """rsv.test_datetime >= '%s' and rsv.test_datetime <= '%s'""" % (date_from, date_to)
        # if state == 'failed':
        #     where += """ AND rsv.state IN ('fail_booking', 'fail_issue')"""
        # where += """ AND rsv.state IN ('partial_issued', 'issued')"""
        if agent_id:
            where += """ AND rsv.agent_id = %s""" % agent_id
        if provider_type and provider_type != 'all':
            where += """ AND provider_type.code = '%s' """ % provider_type
        if state:
            where += """ AND (rsv.state = '%s' OR rsv.state = 'reissue') """ % state
        if state_vendor and state_vendor != 'all':
            where += """ AND rsv.state_vendor = '%s' """ % state_vendor
        return where

    ################
    #   All of ORDER function to build ORDER BY function in SQL
    #   name of the function correspond to respected SELECT, FORM, WHERE, GROUP BY functions for easy development
    ################
    @staticmethod
    def _order_by():
        return """
        test_datetime, rsv.name, psg.name
        """

    def _lines(self, period_mode, date_from, date_to, agent_id, provider_type, state, state_vendor):
        # SELECT
        query = 'SELECT ' + self._select()

        # FROM
        query += 'FROM ' + self._from(provider_type)

        # WHERE
        query += 'WHERE ' + self._where(period_mode, date_from, date_to, agent_id, provider_type, state, state_vendor)

        # ORDER BY
        query += 'ORDER BY ' + self._order_by()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function handle preparation to call query builder for service charge
    def _get_lines_data(self, period_mode, date_from, date_to, agent_id, provider_type, state, state_vendor):
        lines = []
        if provider_type != 'all':
            lines = self._lines(period_mode, date_from, date_to, agent_id, provider_type, state, state_vendor)
            lines = self._convert_data(lines, provider_type)
        else:
            provider_types = variables.PROVIDER_TYPE
            for provider_type in provider_types:
                report_lines = self._lines(period_mode, date_from, date_to, agent_id, provider_type, state, state_vendor)
                report_lines = self._convert_data(report_lines, provider_type)
                for line in report_lines:
                    lines.append(line)
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _convert_data(self, lines, provider_type):
        for rec in lines:
            try:
                rec['test_datetime'] = self._datetime_user_context(rec['test_datetime'])
            except:
                pass
            # rec['state'] = variables.BOOKING_STATE_STR[rec['state']] if rec['state'] else ''  # STATE_OFFLINE_STR[rec['state']]
        return lines

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Recap Transaction Report: ' + data_form['subtitle']

    def _prepare_values(self, data_form):
        data_form['state'] = 'issued'
        period_mode = data_form['period_mode']
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        # if not data_form['state']:
        #     data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        state = data_form['state']
        state_vendor = data_form['state_vendor']
        provider_type = data_form['provider_type']
        lines = self._get_lines_data(period_mode, date_from, date_to, agent_id, provider_type, state, state_vendor)
        self._report_title(data_form)

        return {
            'lines': lines,
            'data_form': data_form
        }
