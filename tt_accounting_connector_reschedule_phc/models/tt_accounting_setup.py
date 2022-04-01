from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupReschedulePHCInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_reschedule_phc = fields.Boolean('Send Reschedule PHC Transaction', default=False)
