from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class AgentReportRecapAfterSales(models.Model):
    _name = 'report.tt_agent_report_recap_aftersales.agent_report_recap'
    _description = 'Recap After Sales'

    ################
    #   All of select function to build SELECT function in SQL
    ################

    # this select function responsible to build query to produce the neccessary report
    @staticmethod
    def _select():
        return """
            rsv.id, rsv.name as after_sales_number, rsv.state, creates.id as creator_id, creates_partner.name as create_by,
            finalized_partner.name as finalized_by, rsv.referenced_pnr, rsv.referenced_document, rsv.admin_fee,
            rsv.admin_fee_ho as ho_commission, rsv.admin_fee_agent as agent_commission, rsv.total_amount, rsv.create_date,
            agent.name as agent_name, agent.email as agent_email,
            currency.name as currency_name, customer_parent.name as customer_parent_name,
            customer_parent_type.name as customer_parent_type_name,
            agent_type.name as agent_type_name, ledger.id as ledger_id, ledger.ref as ledger_name,
            ledger.debit, ledger.credit, ledger_agent.name as ledger_agent_name,
            ledger.transaction_type as ledger_transaction_type, ledger.display_provider_name as ledger_provider,
            ledger.description as ledger_description
            """

    @staticmethod
    def _sel_refund():
        return """
            , rsv.refund_amount as expected_amount, rsv.approve_date as finalized_date, refund_type.name as after_sales_category
            """

    @staticmethod
    def _sel_reschedule():
        return """
            , rsv.reschedule_amount as expected_amount, rsv.pnr, rsv.final_date as finalized_date, rsv.reschedule_type_str as after_sales_category
            """

    ################
    #   All of FROM function to build FROM function in SQL
    #   name of the function correspond to respected SELECT functions for easy development
    ################
    @staticmethod
    def _from(after_sales_type):
        # query = """tt_ledger """
        if after_sales_type == 'refund':
            query = """tt_refund rsv """
        else:
            query = """tt_reschedule rsv """

        query += """LEFT JOIN tt_agent agent ON rsv.agent_id = agent.id
        LEFT JOIN tt_customer_parent customer_parent ON rsv.customer_parent_id = customer_parent.id
        LEFT JOIN tt_customer_parent_type customer_parent_type ON customer_parent_type.id = rsv.customer_parent_type_id
        LEFT JOIN tt_agent_type agent_type ON agent_type.id = rsv.agent_type_id
        LEFT JOIN res_currency currency ON currency.id = rsv.currency_id
        """

        if after_sales_type == 'refund':
            query += """LEFT JOIN tt_refund_type refund_type ON refund_type.id = rsv.refund_type_id """
            query += """LEFT JOIN tt_ledger ledger ON ledger.refund_id = rsv.id AND ledger.is_reversed = 'FALSE' """
        else:
            query += """LEFT JOIN tt_ledger ledger ON ledger.reschedule_id = rsv.id AND ledger.is_reversed = 'FALSE' """

        query += """LEFT JOIN tt_agent ledger_agent ON ledger_agent.id = ledger.agent_id
        LEFT JOIN res_users creates ON creates.id = rsv.create_uid
        LEFT JOIN res_partner creates_partner ON creates.partner_id = creates_partner.id
        """

        if after_sales_type == 'refund':
            query += """LEFT JOIN res_users finalize ON finalize.id = rsv.approve_uid
                        LEFT JOIN res_partner finalized_partner ON finalize.partner_id = finalized_partner.id
                        """
        else:
            query += """LEFT JOIN res_users finalize ON finalize.id = rsv.final_uid
                        LEFT JOIN res_partner finalized_partner ON finalize.partner_id = finalized_partner.id
                        """
        return query

    ################
    #   All of WHERE function to build WHERE function in SQL
    #   name of the function correspond to respected SELECT, FORM functions for easy development
    ################
    @staticmethod
    def _where(date_from, date_to, agent_id, ho_id, customer_parent_id, after_sales_type, state, currency_id):
        where = """rsv.create_date >= '%s' and rsv.create_date <= '%s'""" % (date_from, date_to)
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
        if after_sales_type == 'refund':
            where += """ AND (rsv.state = 'approve' OR rsv.state = 'payment' OR rsv.state = 'approve_cust' OR rsv.state = 'done') """
        else:
            where += """ AND (rsv.state = 'validate' OR rsv.state = 'final' OR rsv.state = 'done') """
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

    ################
    #   Function to build the full query
    #   Within this function we will call the SELECT function, FROM function, WHERE function, etc
    #   for more information of what each query do, se explanation above every select function
    #   name of select function is the same as the _lines_[function name] or get_[function_name]
    ################
    def _lines(self, date_from, date_to, agent_id, ho_id, customer_parent_id, after_sales_type, state, currency_id):
        # SELECT
        query = 'SELECT ' + self._select()
        if after_sales_type == 'refund':
            query += self._sel_refund()
        else:
            query += self._sel_reschedule()

        # FROM
        query += 'FROM ' + self._from(after_sales_type)

        # WHERE
        query += 'WHERE ' + self._where(date_from, date_to, agent_id, ho_id, customer_parent_id, after_sales_type, state, currency_id)

        # 'GROUP BY' + self._group_by() + \
        query += 'ORDER BY ' + self._order_by()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    # this function handle preparation to call query builder for service charge
    def _get_lines_data(self, date_from, date_to, agent_id, ho_id, customer_parent_id, after_sales_type, state, currency_id):
        after_sales_type_dict = {
            'refund': 'Refund',
            'after_sales': 'After Sales'
        }
        lines = []
        if after_sales_type != 'all':
            if after_sales_type == 'after_sales':
                try:
                    self.env['tt.reschedule']
                except:
                    _logger.info('After Sales module is not installed.')
                    raise Exception('After Sales module is not installed.')
            lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, after_sales_type, state, currency_id)
            lines = self._convert_data(lines, after_sales_type)
            lines = self._convert_data_commission(lines, after_sales_type)
            for line in lines:
                line['after_sales_type'] = after_sales_type_dict.get(after_sales_type, '')
        else:
            after_sales_types = ['refund', 'after_sales']
            try:
                self.env['tt.reschedule']
            except:
                after_sales_types.remove('after_sales')
                _logger.info('After Sales module is not installed.')
            for after_sales_type in after_sales_types:
                report_lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, after_sales_type, state, currency_id)
                report_lines = self._convert_data(report_lines, after_sales_type)
                report_lines = self._convert_data_commission(report_lines, after_sales_type)
                for line in report_lines:
                    line['after_sales_type'] = after_sales_type_dict.get(after_sales_type, '')
                    lines.append(line)
        return lines

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _convert_data(self, lines, after_sales_type):
        for rec in lines:
            rec['create_date'] = self._datetime_user_context(rec['create_date'])
            try:
                rec['finalized_date'] = self._datetime_user_context(rec['finalized_date'])
            except:
                pass
            # rec['state'] = variables.BOOKING_STATE_STR[rec['state']] if rec['state'] else ''  # STATE_OFFLINE_STR[rec['state']]
        return lines

    def _convert_data_commission(self, lines, after_sales_type):
        for rec in lines:
            if rec['ledger_transaction_type'] == 3: #HITUNG CREDIT PADA LEDGER TYPE COMMISSION
                rec['debit'] -= rec['credit']
        return lines

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Recap After Sales Report: ' + data_form['subtitle']

    def _prepare_values(self, data_form):
        data_form['state'] = 'issued'
        data_form['is_ho'] = (self.env.user.has_group('tt_base.group_tt_tour_travel') and self.env.user.agent_id.is_ho_agent) or self.env.user.has_group('base.group_erp_manager')
        if self.env.user.has_group('tt_base.group_tt_corpor_user'):
            data_form['is_corpor'] = True
        ho_obj = False
        if data_form.get('ho_id'):
            ho_obj = self.env['tt.agent'].sudo().browse(int(data_form['ho_id']))
        if not ho_obj:
            ho_obj = self.env.user.agent_id.ho_id
        data_form['ho_name'] = ho_obj and ho_obj.name or self.env.ref('tt_base.rodex_ho').sudo().name
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        # if not data_form['state']:
        #     data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        ho_id = data_form['ho_id']
        customer_parent_id = data_form['customer_parent_id']
        state = data_form['state']
        after_sales_type = data_form['after_sales_type']
        currency_id = data_form.get('currency_id', '')
        # lines = self._get_lines_data_search(date_from, date_to, agent_id, provider_type, state)
        lines = self._get_lines_data(date_from, date_to, agent_id, ho_id, customer_parent_id, after_sales_type, state, currency_id) #BOOKING
        # second_lines = []
        self._report_title(data_form)

        return {
            'lines': lines,
            'data_form': data_form
        }
