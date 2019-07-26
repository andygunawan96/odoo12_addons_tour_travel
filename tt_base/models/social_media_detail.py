from odoo import models, fields, api


class SocialMediaDetail(models.Model):
    _name = 'social.media.detail'
    _rec_name = 'name'
    _description = 'Tour & Travel - Social Media Detail'

    name = fields.Char('Name')
    type_id = fields.Many2one('res.social.media.type', 'Social Media Type')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    customer_id = fields.Many2one('tt.customer', 'Customer', store=True)
    active = fields.Boolean('Active', default=True)
