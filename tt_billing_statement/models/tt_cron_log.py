from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

class TtCronLogInhBill(models.Model):
    _inherit = 'tt.cron.log'

    def cron_create_billing_statement(self):
        try:
            self.env['tt.customer.parent'].cron_create_billing_statement()
        except Exception as e:
            try:
                request = {
                    'code': 9903,
                    'message': str(e),
                    "title": 'CRON BILLING STATEMENT'
                }
                api_con_obj = self.env['tt.api.con']
                return api_con_obj.send_request_to_gateway('%s/notification' % (api_con_obj.url),
                                                    request
                                                    , 'notification_code')
            except:
                pass
            self.create_cron_log_folder()
            self.write_cron_log('auto create billing statement')
