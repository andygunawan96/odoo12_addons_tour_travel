from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)


class TtAccountingSetupHotelInh(models.Model):
    _inherit = 'tt.accounting.setup'

    is_send_hotel = fields.Boolean('Send Hotel Transaction', default=False)
