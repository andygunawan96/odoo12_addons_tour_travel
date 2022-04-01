from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupRescheduleInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_reschedule = fields.Boolean('Send Reschedule Transaction', default=False)
