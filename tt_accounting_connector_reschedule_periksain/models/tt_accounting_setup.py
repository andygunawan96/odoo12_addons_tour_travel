from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupReschedulePeriksainInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_reschedule_periksain = fields.Boolean('Send Reschedule Periksain Transaction', default=False)
