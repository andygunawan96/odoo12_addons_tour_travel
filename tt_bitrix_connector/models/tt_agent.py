from odoo import models, fields, api, _
import logging, traceback,pytz

_logger = logging.getLogger(__name__)

class TtAgent(models.Model):
    _inherit = 'tt.agent'

    is_using_bitrix = fields.Boolean('Is Using Bitrix', default=False)
