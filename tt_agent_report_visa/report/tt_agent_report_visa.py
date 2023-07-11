from odoo import models, api, _
from odoo.exceptions import UserError
import pytz, datetime

import logging
_logger = logging.getLogger(__name__)


class AgentReportVisaModel(models.AbstractModel):
    _name = 'report.tt_agent_report_visa.agent_report_visa'
    _description = 'Visa'

    @staticmethod
    def _select():
        return """
        vs.id, vs.name, tcd.first_name || ' ' || tcd.last_name as contact_person, vs.contact_name, rc.name as country_name,
        top.title || ' ' || top.first_name || ' ' || top.last_name as pass_name, top.age, vs.departure_date, vs.issued_date, 
        vs.in_process_date, vs.done_date, vs.state, vs.state_visa, rp.name as issued_name, tvp.immigration_consulate, 
        tvp.visa_type, tl.debit as commission
        """

    @staticmethod
    def _from():
        return """
        tt_reservation_visa vs
        LEFT JOIN tt_customer tcd ON vs.contact_id = tcd.id
        LEFT JOIN res_country rc ON vs.country_id = rc.id
        LEFT JOIN tt_reservation re ON re.provider_type_id = vs.provider_type_id
        LEFT JOIN tt_reservation_visa_order_passengers top ON top.visa_id = vs.id
        LEFT JOIN tt_reservation_visa_pricelist tvp ON tvp.id = top.pricelist_id
        LEFT JOIN tt_ledger tl ON tl.provider_type_id = vs.provider_type_id AND tl.transaction_type = 3 and tl.ref = vs.name
        LEFT JOIN res_users ru ON ru.id = vs.issued_uid
        LEFT JOIN res_partner rp ON rp.id = ru.partner_id
        """

    @staticmethod
    def _where(date_from, date_to, state, agent_id, ho_id):
        where = """vs.create_date >= '%s' and vs.create_date <= '%s'
                 """ % (date_from, date_to)
        if state and state != 'all':
            where += """ AND vs.state_visa IN ('""" + state + """')"""
        if ho_id:
            where += """ AND vs.ho_id = %s """ % ho_id
        if agent_id:
            # todo: buat kondisi jika agent id null
            where += """ AND vs.agent_id = """ + str(agent_id)
        return where

    @staticmethod
    def _group_by():
        return """
        vs.id, rp.id, rp.name, ru.id, vs.state, tvp.visa_type, tcd.first_name, tcd.last_name, top.title, 
        top.first_name, top.last_name, top.age, rc.name, tvp.immigration_consulate, tl.debit
        """

    @staticmethod
    def _order_by():
        return """
        vs.id
        """

    def _lines(self, date_from, date_to, agent_id, ho_id, state):
        query = 'SELECT ' + self._select() + \
                'FROM ' + self._from() + \
                'WHERE ' + self._where(date_from, date_to, state, agent_id, ho_id) + \
                ' GROUP BY ' + self._group_by() + \
                ' ORDER BY ' + self._order_by()
        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def edit_data(self, line_list):
        odoobot_user = self.env['res.users'].sudo().search([('id', '=', 1), ('active', '=', False)])
        tz = odoobot_user.tz
        local = pytz.timezone(tz)
        for line in line_list:
            visa_obj = self.env['tt.reservation.visa'].search([('id', '=', line.get('id'))], limit=1)
            line['total'] = visa_obj.total
            line['total_nta'] = visa_obj.total_nta
            if line['issued_date']:
                local_dt = line['issued_date']
                line['issued_date'] = local_dt.astimezone(local)
            if line['in_process_date']:
                local_dt = line['in_process_date']
                line['in_process_date'] = local_dt.astimezone(local)
            if line['done_date']:
                local_dt = line['done_date']
                line['done_date'] = local_dt.astimezone(local)
        return line_list

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Visa Report: ' + data_form['subtitle']

    def _prepare_values(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        ho_id = data_form['ho_id']
        state = data_form['state']
        line_list = []
        lines = self._lines(date_from, date_to, agent_id, ho_id, state)  # main data
        for line in lines:
            line_list.append(line)
        self.edit_data(line_list)
        self._report_title(data_form)

        return {
            'lines': line_list,
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
