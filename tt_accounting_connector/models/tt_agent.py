from odoo import api,models,fields,_
import logging,traceback

_logger = logging.getLogger(__name__)


class TtAgent(models.Model):
    _inherit = 'tt.agent'

    is_sync_to_acc = fields.Boolean('Sync Transactions to Accounting Software', default=True)
    is_use_ext_credit_cor = fields.Boolean('Use External Credit Limit for Corporate(s)')
    ext_credit_cor_acq_id = fields.Many2one('payment.acquirer', 'External Credit Limit Acquirer')
