from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupPPOBInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_ppob = fields.Boolean('Send PPOB Transaction', default=False)
