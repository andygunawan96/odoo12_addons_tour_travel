from odoo import api,models,fields
from ...tools.ERR import RequestException
import time,logging, pytz
from datetime import datetime

_logger = logging.getLogger(__name__)

class TtLedgerApi(models.Model):
    _name = 'tt.ledger.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.ledger'

    def action_call(self, table_obj, action, data, context):
        if action == 'test_ledger':
            res = table_obj.create_ledger_vanilla(False,
                                                  False,
                                                  'TEST LEDGER CREATE',
                                                  'TEST ##',
                                                  2,
                                                  12,
                                                  self.env.user.id,
                                                  5,
                                                  False,
                                                  data,
                                                  credit=0,
                                                  description='TESTING LEDGER FOR CONCURRENT UPDATE'
                                                  )
        elif action == 'history_transaction_ledger':
            res = table_obj.history_transaction_ledger_api(data, context)
        else:
            raise RequestException(999)
        return res