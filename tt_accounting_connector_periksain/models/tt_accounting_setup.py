from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupPeriksainInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_periksain = fields.Boolean('Send Periksain Transaction', default=False)
