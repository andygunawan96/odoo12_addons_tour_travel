from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupTourInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_tour = fields.Boolean('Send Tour Transaction', default=False)
