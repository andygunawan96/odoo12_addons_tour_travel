from odoo import models, fields, api, _
import logging, traceback,pytz
from ...tools import ERR,variables,util
from odoo.exceptions import UserError
from datetime import datetime,timedelta
from ...tools.ERR import RequestException

_logger = logging.getLogger(__name__)


class TtAccountingSetup(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.accounting.setup'
    _description = 'Tour & Travel - Accounting Setup'

    accounting_provider = fields.Selection(variables.ACCOUNTING_VENDOR, 'Accounting Provider', required=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    cycle = fields.Selection([('real_time', 'Real Time'), ('per_batch', 'Per Batch')], 'Send Cycle', default='real_time', required=True)
    is_recon_only = fields.Boolean('Only Send Reconciled Records', default=False)
    sequence = fields.Integer('Sequence', default=20)
    active = fields.Boolean('Active', default='True')
    is_send_topup = fields.Boolean('Send Top Up Transaction', default=False)
    is_send_refund = fields.Boolean('Send Refund Transaction', default=False)

    @api.depends('accounting_provider')
    @api.onchange('accounting_provider')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = dict(self._fields['accounting_provider'].selection).get(self.accounting_provider)
