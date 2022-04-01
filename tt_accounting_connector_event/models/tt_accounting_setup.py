from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupEventInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_event = fields.Boolean('Send Event Transaction', default=False)
