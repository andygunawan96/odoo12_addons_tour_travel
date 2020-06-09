from odoo import models, fields
from odoo.exceptions import UserError
from ...tools import variables, util
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR

import logging
_logger = logging.getLogger(__name__)

class ReportVendorEvent(models.Model):
    _name = 'report.tt_report_vendor_event.report_vendor_event'
    _description = 'Vendor Transaction Event Report'

    @staticmethod
    def _select():
        return """
        transaction.pnr as transaction_pnr, 
        transaction.sales_date as transaction_sales_date,
        transaction.order_number as quantity, 
        transaction.state as state,
        event.name as event_name, 
        event_option.grade as event_option_name, 
        event_option.price as event_option_price,
        booker.name as booker_name
        """

    @staticmethod
    def _from():
        return """
        tt_event_reservation transaction
        LEFT JOIN tt_master_event event ON event.id = transaction.event_id
        LEFT JOIN tt_event_option event_option ON event_option.id = transaction.event_option_id
        LEFT JOIN tt_customer booker ON booker.id = transaction.booker_id
        """

    @staticmethod
    def _where(vendor_id, event_id, state):
        query = "event.event_vendor_id = {} ".format(vendor_id)
        if event_id != 'all':
            query += "AND event.id = {} ".format(event_id)
        if state != 'all':
            query += "AND transaction.transaction_state = {}".format(state)
        return query

    @staticmethod
    def _order_by():
        return """transaction.sales_date
        """

    @staticmethod
    def _report_title(data_form):
        data_form['title'] = 'Report Transaction : ' + data_form['event_name']

    def _lines(self, vendor_id, event_id, state):
        query = "SELECT {} ".format(self._select())
        query += 'FROM {} '.format(self._from())
        query += 'WHERE {} '.format(self._where(vendor_id, event_id, state))
        query += 'ORDER BY {}'.format(self._order_by())

        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def _datetime_user_context(selfself, utc_datetime_string):
        return False

    def _get_lines_data(self, vendor_id, event_name, state):
        lines = self._lines(vendor_id, event_name, state)
        return lines

    def _prepared_valued(self, data_form):
        event_id = data_form['event_name']
        state = data_form['transaction_state']
        vendor_id = data_form['vendor_id']
        line = self._get_lines_data(vendor_id, event_id, state)
        self._report_title(data_form)
        return {
            'lines': line,
            'data_form': data_form
        }