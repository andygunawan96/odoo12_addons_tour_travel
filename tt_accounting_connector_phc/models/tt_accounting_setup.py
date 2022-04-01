from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupPHCInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_phc = fields.Boolean('Send PHC Transaction', default=False)
