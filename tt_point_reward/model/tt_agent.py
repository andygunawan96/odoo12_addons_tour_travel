from odoo import api,models,fields,_
import logging,traceback

_logger = logging.getLogger(__name__)


class TtAgentPointInh(models.Model):
    _inherit = 'tt.agent'

    is_use_point_reward = fields.Boolean('Is Use Point Reward', default=False)

    def get_is_use_point_reward(self):
        return self.is_use_point_reward
