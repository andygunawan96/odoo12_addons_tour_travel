from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupAirlineInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_airline = fields.Boolean('Send Airline Transaction', default=False)
