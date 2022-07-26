from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)

class TtReservation(models.Model):

    _inherit = 'tt.reservation'

    is_get_point_reward = fields.Boolean('Is Get Point Reward', default=False)
    is_use_point_reward = fields.Boolean('Is Use Point Reward', default=False)
