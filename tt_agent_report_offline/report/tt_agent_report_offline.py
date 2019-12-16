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
        return """ro.id, ro.create_date, ro.name, agent.id agent_id, agent.name agent_name, 
        tcd.first_name || ' ' || tcd.last_name contact_person, tpt.code as provider_type, 
        COALESCE(ttc.name, tp.name) provider, rol.pnr, ro.description, ro.confirm_date, pconf.name confirm_by, 
        ro.issued_date, piss.name issued_by, ro.total total, ro.state, ro.state_offline """

    @staticmethod
    def _from_lines():
        return """
        tt_reservation_offline ro 
        LEFT JOIN tt_reservation_offline_lines rol ON rol.booking_id = ro.id
        LEFT JOIN tt_agent agent ON agent.id = ro.agent_id 
        LEFT JOIN tt_customer tcd ON ro.contact_id = tcd.id 
        LEFT JOIN tt_provider_type tpt ON tpt.id = ro.provider_type_id
        LEFT JOIN tt_transport_carrier ttc ON ttc.id = rol.carrier_id 
        LEFT JOIN tt_provider tp on tp.id = rol.provider_id
        LEFT JOIN res_users uconf ON uconf.id = ro.confirm_uid 
        LEFT JOIN res_partner pconf ON pconf.id = uconf.partner_id 
        LEFT JOIN res_users uiss ON uiss.id = ro.issued_uid 
        LEFT JOIN res_partner piss ON piss.id = uiss.partner_id
        """

    @staticmethod
    def _where_lines(date_from, date_to, agent_id, state, provider_type):
        where = """ro.create_date >= '%s' and ro.create_date <= '%s'
         """ % (date_from, date_to)
        if state and state != 'all':
            where += """ AND ro.state = '%s'""" % state
        if provider_type and provider_type != 'all':
            where += """ AND tpt.code = '%s'""" % provider_type
        if agent_id:
            where += """ AND ro.agent_id = %s """ % agent_id
        return where

    @staticmethod
    def _group_by_lines():
        return """
        ro.id, tcd.id, pconf.id, piss.id, agent.id, tpt.id, rol.id, tp.id, ttc.id
        """

    @staticmethod
    def _order_by_lines():
        return """
        ro.id
        """

    def _lines(self, date_from, date_to, agent_id, state, provider_type):
        query = 'SELECT ' + self._select_lines() + \
                'FROM ' + self._from_lines() + \
                ' WHERE ' + self._where_lines(date_from, date_to, agent_id, state, provider_type) + \
                'GROUP BY ' + self._group_by_lines() + \
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
    def _where_lines_commission(date_from, date_to, agent_id, state, provider_type):
        where = """ro.create_date >= '%s' AND ro.create_date <= '%s '
                AND tl.transaction_type = 3""" % (date_from, date_to)
        if state and state != 'all':
            where += """ AND ro.state = '%s'""" % state
        if provider_type and provider_type != 'all':
            where += """ AND tpt.code = '%s'""" % provider_type
        if agent_id:
            where += """ AND tl.agent_id = %s """ % agent_id
        return where

    @staticmethod
    def group_by_lines_commission():
        return """tl.id, ro.id, tpt.id """

    @staticmethod
    def order_by_lines_commission():
        return """ro.id"""

    def _lines_commission(self, date_from, date_to, agent_id, state, provider_type):
        query = 'SELECT ' + self._select_lines_commission() + \
                'FROM ' + self._from_lines_commission() + \
                'WHERE ' + self._where_lines_commission(date_from, date_to, agent_id, state, provider_type) + \
                'GROUP BY ' + self.group_by_lines_commission() + \
                'ORDER BY ' + self.order_by_lines_commission()
        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _datetime_user_context(self, utc_datetime_string):
        value = fields.Datetime.from_string(utc_datetime_string)
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S')

    def _convert_data(self, lines):
        odoobot_user = self.env['res.users'].sudo().search([('id', '=', 1), ('active', '=', False)])
        tz = odoobot_user.tz
        local = pytz.timezone(tz)
        for rec in lines:
            # STATE_OFFLINE[rec['state']] if rec['state'] else ''
            rec.update({
                'create_date': self._datetime_user_context(rec['create_date']),
                'nta_amount': rec['total'] if rec['total'] else 0,
                'state': variables.BOOKING_STATE_STR[rec['state']] if rec['state'] else '',
                'state_offline': STATE_OFFLINE_STR[rec['state_offline']] if rec['state_offline'] else '',
                'provider_type': rec['provider_type'].capitalize() if rec['provider_type'] else rec['provider_type'],
                'commission': 0
            })
            if rec['confirm_date']:
                local_dt = rec['confirm_date']
                rec['confirm_date'] = local_dt.astimezone(local).strftime('%Y-%m-%d %H:%M:%S')
            if rec['issued_date']:
                local_dt = rec['issued_date']
                rec['issued_date'] = local_dt.astimezone(local).strftime('%Y-%m-%d %H:%M:%S')
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
        agent_id = data_form['agent_id']
        state = data_form['state']
        provider_type = data_form['provider_type']
        lines = self._lines(date_from, date_to, agent_id, state, provider_type)
        lines_commission = self._lines_commission(date_from, date_to, agent_id, state, provider_type)
        lines = self._convert_data(lines)
        lines = self._convert_data2(lines, lines_commission)
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
