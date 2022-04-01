from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupOfflineInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_offline = fields.Boolean('Send Offline Transaction', default=False)
