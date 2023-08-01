from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

class TtCronLogInhBill(models.Model):
    _inherit = 'tt.cron.log'

    def cron_create_billing_statement(self):
        # 28 Jul update per HO
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                self.env['tt.customer.parent'].cron_create_billing_statement(ho_obj.id)
                self.env['tt.agent'].cron_create_billing_statement(ho_obj.id)
            except Exception as e:
                try:
                    request = {
                        'code': 9903,
                        'message': str(e),
                        "title": 'CRON BILLING STATEMENT'
                    }
                    api_con_obj = self.env['tt.api.con']
                    ## tambah context
                    ## kurang test
                    return api_con_obj.send_request_to_gateway('%s/notification' % (api_con_obj.url),
                                                        request
                                                        , 'notification_code', ho_id=ho_obj.id)
                except:
                    pass
                self.create_cron_log_folder()
                self.write_cron_log('auto create billing statement', ho_id=ho_obj.id)
