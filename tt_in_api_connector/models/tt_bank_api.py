from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException

class TtBankApiCon(models.Model):
    _name = 'tt.bank.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.bank.con'

    def get_balance(self, provider_ho_data_obj, req, ho_id):
        data = {
            'account_number': provider_ho_data_obj.bank_account_id.bank_account_number_without_dot, # '511.01.50000'
            'provider': provider_ho_data_obj.provider_id.code, #'bca',
            'ho_id': ho_id
        }
        return self.send_request_to_gateway('%s/bank' % (self.url), data,'get_balance', ho_id=ho_id)

    def get_transaction(self,req, ho_id):

        data = {
            'account_number': req['account_number'], #'511.01.50000',
            'provider': req['provider'], #'bca',
            'startdate': req['startdate'], # '2019-11-01',
            'enddate': req['enddate'], #'2019-11-05',
            'is_snap': req.get('is_snap')
        }
        return self.send_request_to_gateway('%s/bank' % (self.url), data, 'get_transaction',timeout=60, ho_id=ho_id)