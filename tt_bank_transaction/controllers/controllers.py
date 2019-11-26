from odoo import http
from odoo.http import request
import json
import datetime

class TtBankStatement(http.Controller):
    @http.route('/get_bank_statement', type='http', auth='public')
    def get_bank_transaction(self, **kw):
        # data = {
        #     'account_number': 5110150000,
        #     'provider': 'bca',
        #     'startdate': datetime.datetime.today().strftime("%Y-%m-%d"),
        #     'enddate': datetime.datetime.today().strftime("%Y-%m-%d"),
        # }
        data = {
            'account_number': 5110150000,
            'provider': 'bca',
            'startdate': '2019-11-01',
            'enddate': '2019-11-05',
        }
        result = request.env['tt.bank.transaction'].get_data(data)

        return 0

    @http.route('/top_up_validator', type='http', auth='public')
    def top_up_validator(self, **kwargs):
        result = request.env['tt.bank.transaction'].process_data("0")

        return 0