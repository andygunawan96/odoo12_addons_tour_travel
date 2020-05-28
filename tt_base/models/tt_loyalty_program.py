from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime, timedelta
import json, logging


_logger = logging.getLogger(__name__)


class TtLoyaltyProgram(models.Model):
    _name = 'tt.loyalty.program'
    _inherit = 'tt.history'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description', default='')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        res = {
            'name': self.name,
            'description': self.description and self.description or '',
        }
        return res
