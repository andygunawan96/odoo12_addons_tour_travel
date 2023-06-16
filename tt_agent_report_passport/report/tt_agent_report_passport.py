from odoo import models, api, fields, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AgentReportPassportModel(models.AbstractModel):
    _name = 'report.tt_agent_report_passport.agent_report_passport'
    _description = 'Passport'

    @staticmethod
    def _select():
        return """
        ps.name, tcd.first_name || ' ' || tcd.last_name as contact_person, ps.contact_name, rc.name as country_name,
        top.title || ' ' || top.first_name || ' ' || top.last_name as pass_name, top.age age, ps.departure_date, 
        ps.issued_date, ps.in_process_date, ps.done_date, ps.state, ps.state_passport, rp.name as issued_name, 
        tpp.immigration_consulate, tpp.passport_type, tl.debit as commission, ps.total, ps.total_nta
        """

    @staticmethod
    def _from():
        return """
        tt_reservation_passport ps 
        LEFT JOIN tt_customer tcd ON ps.contact_id = tcd.id
        LEFT JOIN res_country rc ON ps.country_id = rc.id
        LEFT JOIN tt_reservation re ON re.provider_type_id = ps.provider_type_id
        LEFT JOIN tt_reservation_passport_order_passengers top ON top.passport_id = ps.id
        LEFT JOIN tt_reservation_passport_pricelist tpp ON tpp.id = top.pricelist_id
        LEFT JOIN tt_ledger tl ON tl.provider_type_id = ps.provider_type_id AND tl.transaction_type = 3 and tl.ref = ps.name
        LEFT JOIN res_users ru ON ru.id = ps.issued_uid
        LEFT JOIN res_partner rp ON rp.id = ru.partner_id
        """

    @staticmethod
    def _where(date_from, date_to, state, agent_id, ho_id):
        where = """ps.create_date >= '%s' and ps.create_date <= '%s'
                     """ % (date_from, date_to)
        if state and state != 'all':
            where += """ AND ps.state_passport IN ('""" + state + """')"""
        if ho_id:
            where += """ AND ps.ho_id = %s """ % ho_id
        if agent_id:
            # todo: buat kondisi jika agent id null
            where += """ AND ps.agent_id = """ + str(agent_id)
        return where

    @staticmethod
    def _group_by():
        return """
            ps.id, rp.id, rp.name, ru.id, ps.state, tpp.passport_type, tcd.first_name, tcd.last_name, top.age,
            top.title, top.first_name, top.last_name, rc.name, tpp.immigration_consulate, tl.debit
            """

    @staticmethod
    def _order_by():
        return """
            ps.id
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

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Passport Report: ' + data_form['subtitle']

    def _prepare_values(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        if not data_form['state']:
            data_form['state'] = 'all'
        agent_id = data_form['agent_id']
        ho_id = data_form['ho_id']
        state = data_form['state']
        lines = self._lines(date_from, date_to, agent_id, ho_id, state)
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
