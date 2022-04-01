from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupActivityInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_activity = fields.Boolean('Send Activity Transaction', default=False)
