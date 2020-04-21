from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, date, timedelta
_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_expire_top_up(self):
        try:
            new_top_up = self.env['tt.top.up'].search([('state', 'in', ['confirm','request','expired']),])
            for top_up in new_top_up:
                try:
                    if datetime.now() >= (top_up.due_date or datetime.min):
                        top_up.action_expired_top_up()
                except Exception as e:
                    _logger.error('%s something failed during expired cron.\n' % (top_up.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-reset payment unique amount')

    def cron_expire_refund(self):
        try:
            new_refund = self.env['tt.refund'].search([('state', '=', 'sent')])
            for rec in new_refund:
                try:
                    if datetime.now() >= rec.hold_date:
                        rec.action_expired()
                except Exception as e:
                    _logger.error('%s something failed during expired cron.\n' % (rec.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-expired refund')

    def cron_action_approve_refund(self):
        try:
            finalized_refunds = self.env['tt.refund'].search([('state', '=', 'final')])
            for rec in finalized_refunds:
                try:
                    if date.today() >= rec.refund_date:
                        rec.action_approve()
                except Exception as e:
                    _logger.error('%s something failed during refund action approve cron.\n' % (rec.name) + traceback.format_exc())
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto-action-approve refund.')

    def cron_inactive_ledger_waiting_list(self):
        try:
            old_recs = self.env['tt.ledger.waiting.list'].search([('is_in_transaction','=',True),
                                                                       ('create_date', '<=', datetime.today() - timedelta(minutes=5))])
            for rec in old_recs:
                rec.is_in_transaction = False
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('auto expired ledger waiting list')