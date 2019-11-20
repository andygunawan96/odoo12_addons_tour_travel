from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, date
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_update_installment_invoice(self):
        try:
            installment_objs = self.env['tt.installment.invoice'].sudo().search([('state', 'in', ['open', 'trouble'])])
            for rec in installment_objs:
                if rec.agent_invoice_id.state == 'paid':
                    rec.action_set_to_done()
                elif rec.due_date < date.today() and rec.state_invoice != 'trouble':
                    rec.action_trouble()

        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('Update installment invoice Tour')
