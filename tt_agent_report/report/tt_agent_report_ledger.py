from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AgentReportLedger(models.AbstractModel):
    _name = 'report.tt_agent_report.agent_report_ledger'
    _description = 'Ledger Report'

    @staticmethod
    def _select():
        return """
        lg.id, lg.date, lg.ref, lg.display_provider_name, tpt.name provider_type, lg.pnr, agt.name agent, 
        agt_type.name agent_type, lg.description, rp.name issued_by, lg.transaction_type, lg.debit, lg.credit, lg.balance
        """

    @staticmethod
    def _from():
        return """
        tt_ledger lg
        LEFT JOIN tt_provider_type tpt ON lg.provider_type_id = tpt.id
        LEFT JOIN tt_agent agt ON lg.agent_id = agt.id
        LEFT JOIN tt_agent_type agt_type ON lg.agent_type_id = agt_type.id
        LEFT JOIN res_users ru ON ru.id = lg.issued_uid
        LEFT JOIN res_partner rp ON rp.id = ru.partner_id
        """

    @staticmethod
    def _where(date_from, date_to, agent_id, ho_id):
        where = """lg.create_date >= '%s' and lg.create_date <= '%s'
                         """ % (date_from, date_to)
        if ho_id:
            where += """ AND lg.ho_id = """ + str(ho_id)
        if agent_id:
            where += """ AND lg.agent_id = """ + str(agent_id)
        return where

    @staticmethod
    def _group_by():
        return """
        lg.id, tpt.id, agt.id, agt_type.id, ru.id, rp.id
        """

    @staticmethod
    def _order_by():
        return """
        lg.id
        """

    def _lines(self, date_from, date_to, agent_id, ho_id):
        query = 'SELECT ' + self._select() + \
                'FROM ' + self._from() + \
                'WHERE ' + self._where(date_from, date_to, agent_id, ho_id) + \
                'ORDER BY ' + self._order_by()
        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _convert_data(self, lines):
        transaction_type = dict(self.env['tt.ledger']._fields['transaction_type'].selection)
        for line in lines:
            line.update({
                'transaction_type': transaction_type[line['transaction_type']]
            })
        return lines

    def _get_user_agent_type(self, data_form):
        if self.env.user.agent_id.is_ho_agent:
            data_form['agent_type'] = 'ho'
        else:
            data_form['agent_type'] = 'non ho'

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Ledger Report: ' + data_form['subtitle']

    def _prepare_values(self, data_form):
        date_from = data_form['date_from']
        date_to = data_form['date_to']
        agent_id = data_form['agent_id']
        ho_id = data_form['ho_id']
        line_list = []

        lines = self._lines(date_from, date_to, agent_id, ho_id)  # main data
        lines = self._convert_data(lines)
        for line in lines:
            line_list.append(line)
        self._get_user_agent_type(data_form)
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
