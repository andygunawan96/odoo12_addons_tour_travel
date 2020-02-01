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
            self.create_cron_log_folder()
            self.write_cron_log('auto create billing statement')
