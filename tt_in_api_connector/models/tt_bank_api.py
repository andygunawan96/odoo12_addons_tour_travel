from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException

class TtBankApiCon(models.Model):
    _name = 'tt.bank.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.bank.con'

    def get_balance(self, req):
        data = {
            'account_number': req['account_number'], # '511.01.50000'
            'provider': req['provider'] #'bca'
        }
        return self.send_request_to_gateway('%s/bank' % (self.url), data,'get_balance')

    def get_transaction(self,req):

        data = {
            'account_number': req['account_number'], #'511.01.50000',
            'provider': req['provider'], #'bca',
            'startdate': req['startdate'], # '2019-11-01',
            'enddate': req['enddate'] #'2019-11-05',
        }
        return self.send_request_to_gateway('%s/bank' % (self.url), data, 'get_transaction',timeout=60)