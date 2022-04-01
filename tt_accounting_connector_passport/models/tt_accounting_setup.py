from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupPassportInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_passport = fields.Boolean('Send Passport Transaction', default=False)
