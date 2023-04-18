from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)

class TtPointRewardRules(models.Model):
    _name = "tt.point.reward.rules"
    _inherit = 'tt.history'
    _description = 'Point Reward Rules Model'
    _rec_name = 'name'


    def _compute_get_ho(self):
        if self.env.user.agent_id:
            return self.env.user.agent_id.get_ho_parent_agent().id
        return False

    name = fields.Char("Point Reward Rules Name", required=True, default='Point Reward Rules')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, readonly=True, default=lambda self: self.env.user.company_id.currency_id.id)
    is_gradual_points = fields.Boolean('Is Gradual Points', default=True, help="""Gradual Points ex: price:50,000 for point:10,000 total payment:150,000 agent will get 30,000 points""")
    min_price = fields.Monetary(string='Minimum Price', default=0)
    points = fields.Float(string='Point', default=0)
    ho_id = fields.Many2one('tt.agent', string="Head Office", domain=[('is_ho_agent', '=', True)], default=_compute_get_ho)

