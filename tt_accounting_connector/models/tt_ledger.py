from odoo import api,models,fields,_
from ...tools import util,ERR
import logging,traceback
import json

_logger = logging.getLogger(__name__)


class TtLedger(models.Model):
    _inherit = 'tt.ledger'

    is_sent_to_acc = fields.Boolean('Is Sent to Accounting Software', readonly=True, default=False)

    def set_sent_to_acc_false(self):
        self.sudo().write({
            'is_sent_to_acc': False
        })
