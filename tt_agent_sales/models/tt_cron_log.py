from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, date, timedelta
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_delete_split_invoice_wizard(self):
        try:
            wizard_objs = self.env['tt.split.invoice.wizard'].sudo().search([('create_date', '<=', datetime.today() - timedelta(days=2))])
            for rec in wizard_objs:
                rec.sudo().unlink()

            wizard_objs = self.env['tt.merge.invoice.wizard'].sudo().search([('create_date', '<=', datetime.today() - timedelta(days=2))])
            for rec in wizard_objs:
                rec.sudo().unlink()

            wizard_objs = self.env['tt.dynamic.print.invoice.wizard'].sudo().search([('create_date', '<=', datetime.today() - timedelta(days=2))])
            for rec in wizard_objs:
                rec.sudo().unlink()

        except Exception as e:
            self.create_cron_log_folder()
            ## tidak tahu pakai context apa
            self.write_cron_log('Update installment invoice Tour')
