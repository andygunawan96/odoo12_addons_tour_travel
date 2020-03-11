from odoo import api,models,fields
from ...tools.ERR import RequestException
import time,logging, pytz, datetime

_logger = logging.getLogger(__name__)

class TtLedgerApi(models.Model):
    _name = 'tt.ledger.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.ledger'

    def action_call(self, table_obj, action, data, context):
        if action == 'test_ledger':
            start_time = time.time()
            res = {'error_code':1028}
            second = False
            while res['error_code'] == 1028 and time.time() - start_time < 60:
                if second:
                    _logger.error("CONCURRENT TIME ERROR %s" % (data['value']))
                res = table_obj.create_ledger_vanilla(False,
                                                      False,
                                                      'TEST LEDGER CREATE',
                                                      'TEST ##',
                                                      datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                                                      2,
                                                      12,
                                                      self.env.user.id,
                                                      5,
                                                      False,
                                                      data['value'],
                                                      credit=0,
                                                      description='TESTING LEDGER FOR CONCURRENT UPDATE'
                                                      )
        else:
            raise RequestException(999)
        return res