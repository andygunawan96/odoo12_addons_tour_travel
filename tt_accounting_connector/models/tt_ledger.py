from odoo import api,models,fields,_
from odoo.exceptions import UserError
from ...tools import util,ERR
import logging,traceback
import json

_logger = logging.getLogger(__name__)


class TtLedger(models.Model):
    _inherit = 'tt.ledger'

    is_sent_to_acc = fields.Boolean('Is Sent to Accounting Software', readonly=True, default=False)

    def set_sent_to_acc_false(self):
        if not self.env.user.has_group('tt_base.group_ledger_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 31')
        self.sudo().write({
            'is_sent_to_acc': False
        })

    def get_allowed_rule(self):
        res = super(TtLedger, self).get_allowed_rule()
        res.update({
            'is_sent_to_acc': (
                True,
                ('is_sent_to_acc',)  ## koma jangan di hapus nanti error tidak loop tupple tetapi string
            )
        })
        return res
