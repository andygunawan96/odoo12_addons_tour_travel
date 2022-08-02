from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)

class TtPointRewardRules(models.Model):
    _name = "tt.point.reward.rules"
    _inherit = 'tt.history'
    _description = 'Point Reward Rules Model'
    _rec_name = 'name'

    name = fields.Char("Point Reward Rules Name", required=True, default='Point Reward Rules')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, readonly=True, default=lambda self: self.env.user.company_id.currency_id.id)
    is_gradual_points = fields.Boolean('Is Gradual Points', default=True, help="""Gradual Points ex: price:50,000 for point:10,000 total payment:150,000 agent will get 30,000 points""")
    min_price = fields.Monetary(string='Minimum Price', default=0)
    points = fields.Monetary(string='Point', default=0)
