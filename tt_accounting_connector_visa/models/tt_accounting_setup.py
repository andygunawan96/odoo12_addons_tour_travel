from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupVisaInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_visa = fields.Boolean('Send Visa Transaction', default=False)
