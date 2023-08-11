from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR
import pytz, datetime

import logging
_logger = logging.getLogger(__name__)


class AgentReportOffline(models.AbstractModel):
    _name = 'report.tt_agent_report_offline.agent_report_offline'
    _description = 'Offline'

    @staticmethod
    def _select_lines():

        # return """* """

        return """
        ro.id as ro_id, ro.name as ro_name, ro.create_date, ro.issued_date as ro_issued_date,
        ro.total as ro_total, ro.state as ro_state, ro.state_offline as ro_state_offline, ro.description as ro_description,
        ro.confirm_date as ro_confirm_date, ro.offline_provider_type as ro_offline_provider_type, 
        ro.pnr as ro_pnr, ro.total_fare as ro_total_fare, ro.total_nta as ro_total_nta, ro.total_commission as ro_total_commission,
        rol.pnr as rol_pnr,
        agent.id as agent_id, agent.name as agent_name,
        customer.first_name as customer_first_name, customer.last_name as customer_last_name,
        provider.name as provider_name,
        provider_type.code as provider_type_name,
        partner_issue.name as issuer_name, partner_confirm.name as confirm_name
        """

        # return """
        # ro.id, ro.create_date, ro.name, agent.id agent_id, agent.name agent_name, ro.offline_provider_type as offline_provider_type,
        # tcd.first_name || ' ' || tcd.last_name as contact_person, tpt.code as provider_type,
        # COALESCE(ttc.name, tp.name) provider, rol.pnr, ro.description, ro.confirm_date, pconf.name confirm_by,
        # ro.issued_date, piss.name issued_by, ro.total total, ro.state, ro.state_offline """

    @staticmethod
    def _select_lines_airline_train():
        return """
                ro.id as ro_id, ro.name as ro_name, ro.create_date, ro.issued_date as ro_issued_date,
                ro.total as ro_total, ro.state as ro_state, ro.state_offline as ro_state_offline, ro.description as ro_description,
                ro.confirm_date as ro_confirm_date, ro.offline_provider_type as ro_offline_provider_type,
                ro.pnr as ro_pnr, ro.total_fare as ro_total_fare, ro.total_nta as ro_total_nta, ro.total_commission as ro_total_commission,
                rol.pnr as rol_pnr,
                departure.name as departure_name, departure.display_name as start_point,
                destination.name as destination_name, destination.display_name as end_point,
                agent.id as agent_id, agent.name as agent_name,
                carrier.name as carrier_name,
                customer.first_name as customer_first_name, customer.last_name as customer_last_name,
                provider.name as provider_name,
                provider_type.code as provider_type_name,
                partner_issue.name as issuer_name, partner_confirm.name as confirm_name
                """

    @staticmethod
    def _from_lines():
        return """
        tt_reservation_offline ro
        LEFT JOIN tt_agent agent ON agent.id = ro.agent_id
        LEFT JOIN tt_customer customer ON customer.id = ro.contact_id
        LEFT JOIN tt_reservation_offline_lines rol ON rol.booking_id = ro.id
        LEFT JOIN tt_provider provider ON provider.id = rol.provider_id
        LEFT JOIN tt_provider_type provider_type ON provider_type.id = ro.provider_type_id
        LEFT JOIN res_users users ON users.id = ro.confirm_uid
        LEFT JOIN res_partner partner_confirm ON partner_confirm.id = users.partner_id
        LEFT JOIN res_users user_issue ON user_issue.id = ro.issued_uid
        LEFT JOIN res_partner partner_issue ON partner_issue.id = user_issue.partner_id
        """

    @staticmethod
    def _from_lines_airline_train():
        return """
            tt_reservation_offline ro
            LEFT JOIN tt_agent agent ON agent.id = ro.agent_id
            LEFT JOIN tt_customer customer ON customer.id = ro.contact_id
            LEFT JOIN tt_reservation_offline_lines rol ON rol.booking_id = ro.id
            LEFT JOIN tt_provider provider ON provider.id = rol.provider_id
            LEFT JOIN tt_destinations departure ON departure.id = rol.origin_id
            LEFT JOIN tt_transport_carrier carrier ON carrier.id = rol.carrier_id
            LEFT JOIN tt_destinations destination ON destination.id = rol.destination_id
            LEFT JOIN tt_provider_type provider_type ON provider_type.id = ro.provider_type_id
            LEFT JOIN res_users users ON users.id = ro.confirm_uid
            LEFT JOIN res_partner partner_confirm ON partner_confirm.id = users.partner_id
            LEFT JOIN res_users user_issue ON user_issue.id = ro.issued_uid
            LEFT JOIN res_partner partner_issue ON partner_issue.id = user_issue.partner_id
        """

    @staticmethod
    def _where_lines(date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type):
        where = """ro.create_date >= '%s' and ro.create_date <= '%s'
         """ % (date_from, date_to)
        if state and state != 'all':
            where += """ AND ro.state_offline = '%s'""" % state
        if provider_type and provider_type != 'all':
            where += """ AND ro.offline_provider_type = '%s'""" % provider_type
        if ho_id:
            where += """ AND ro.ho_id = %s """ % ho_id
        if agent_id:
            where += """ AND ro.agent_id = %s """ % agent_id
        if customer_parent_id:
            where += """ AND ro.customer_parent_id = %s """ % customer_parent_id
        return where

    @staticmethod
    def _group_by_lines():
        # return """
        # ro.id, tcd.id, pconf.id, piss.id, agent.id, tpt.id, rol.id, tp.id, ttc.id
        # """
        return """
        """

    @staticmethod
    def _group_by_lines_airline_train():
        # return """
        #     ro.id, tcd.id, pconf.id, piss.id, agent.id, tpt.id, rol.id, tp.id, ttc.id, departure.name
        #     """

        return """
        """

    @staticmethod
    def _order_by_lines():
        return """
        ro.id
        """

    def _lines(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type):
        query = 'SELECT ' + self._select_lines() + \
                'FROM ' + self._from_lines() +\
                ' WHERE ' + self._where_lines(date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type) + \
                'ORDER BY' + self._order_by_lines()
                # 'GROUP BY ' + self._group_by_lines()
        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _lines_transport(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type):
        query = 'SELECT ' + self._select_lines_airline_train() + \
                'FROM ' + self._from_lines_airline_train() +\
                ' WHERE ' + self._where_lines(date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type) + \
                'ORDER BY' + self._order_by_lines()

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()


    @staticmethod
    def _select_lines_commission():
        return """ro.id, ro.name, tl.agent_id agent_id, tl.debit commission, tpt.code as provider_type """

    @staticmethod
    def _from_lines_commission():
        return """
        tt_ledger tl
        LEFT JOIN tt_reservation_offline ro ON tl.ref = ro.name
        LEFT JOIN tt_provider_type tpt ON tpt.id = ro.provider_type_id  
        """

    @staticmethod
    def _where_lines_commission(date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type):
        where = """ro.create_date >= '%s' AND ro.create_date <= '%s '
                AND tl.transaction_type = 3""" % (date_from, date_to)
        if state and state != 'all':
            where += """ AND ro.state = '%s'""" % state
        if provider_type and provider_type != 'all':
            where += """ AND tpt.code = '%s'""" % provider_type
        if ho_id:
            where += """ AND tl.ho_id = %s """ % ho_id
        if agent_id:
            where += """ AND tl.agent_id = %s """ % agent_id
        if customer_parent_id:
            where += """ AND tl.customer_parent_id = %s """ % customer_parent_id
        return where

    @staticmethod
    def group_by_lines_commission():
        return """tl.id, ro.id, tpt.id """

    @staticmethod
    def order_by_lines_commission():
        return """ro.id"""

    def _lines_commission(self, date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type):
        query = 'SELECT ' + self._select_lines_commission() + \
                'FROM ' + self._from_lines_commission() + \
                'WHERE ' + self._where_lines_commission(date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type) + \
                ' GROUP BY ' + self.group_by_lines_commission() + \
                'ORDER BY ' + self.order_by_lines_commission()
        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _convert_data(self, lines):
        odoobot_user = self.env['res.users'].sudo().search([('id', '=', 1), ('active', '=', False)])
        tz = odoobot_user.tz and odoobot_user.tz or 'utc'
        local = pytz.timezone(tz)
        for i in lines:
            i['create_date'] = self._datetime_user_context(i['create_date'])
            i['commission'] = 0 #will be added in other function
            if i['ro_confirm_date']:
                local_dt = i['ro_confirm_date']
                i['ro_confirm_date'] = local_dt.astimezone(local).strftime('%Y-%m-%d %H:%M:%S')
            if i['ro_issued_date']:
                local_dt = i['ro_issued_date']
                i['ro_issued_date'] = local_dt.astimezone(local).strftime('%Y-%m-%d %H:%M:%S')
        return lines

    @staticmethod
    def _convert_data2(lines, lines_commission):  # ganti nama fungsi nanti
        line_list = []
        line_idx = 0
        data_idx = {}
        for line in lines:
            order_num_match = False
            for idx, line_val in enumerate(line_list):
                if line['name'] == line_val['name']:
                    order_num_match = True
                    if line['pnr']:
                        if line['pnr'] not in line_list[idx]['pnr']:
                            line_list[idx]['pnr'] += ', ' + line['pnr']
                    if line['provider']:
                        if line['provider'] not in line_list[idx]['provider']:
                            line_list[idx]['provider'] += ', ' + line['provider']
                    break
            if not order_num_match:
                data_idx.update({line['id']: line_idx})
                line_list.append(line)
                line_idx += 1
        for rec in lines_commission:
            if rec['id'] in data_idx:
                # Agent Commission
                line = line_list[data_idx[rec['id']]]
                if line['agent_id'] == rec['agent_id']:
                    line['commission'] += rec['commission']
                    line['nta_amount'] -= rec['commission']
        return line_list

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Issued Offline Report: ' + data_form['subtitle']

    @staticmethod
    def duplicate_data(lines):
        # untuk testing jika dimasukkan report dalam jumlah banyak
        new_lines = []
        for i in range(200):
            for line in lines:
                new_lines.append(line)
        return new_lines

    def _prepare_values(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        ho_id = data_form['ho_id']
        agent_id = data_form['agent_id']
        customer_parent_id = data_form['customer_parent_id']
        state = data_form['state']
        provider_type = data_form['provider_type']
        if provider_type == 'airline' or provider_type == 'train':
            lines = self._lines_transport(date_from, date_to, agent_id, ho_id, state, provider_type)
        else:
            lines = self._lines(date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type)
        # lines_commission = self._lines_commission(date_from, date_to, agent_id, ho_id, customer_parent_id, state, provider_type)
        lines = self._convert_data(lines)
        # lines = self._convert_data2(lines, lines_commission)
        self._report_title(data_form)

        return {
            'lines': lines,
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
