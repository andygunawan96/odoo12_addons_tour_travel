from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupTrainInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_train = fields.Boolean('Send Train Transaction', default=False)
