from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime, timedelta
import json, logging


_logger = logging.getLogger(__name__)


class TtLoyaltyProgram(models.Model):
    _name = 'tt.loyalty.program'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description', default='')
    active = fields.Boolean('Active', default=True)
