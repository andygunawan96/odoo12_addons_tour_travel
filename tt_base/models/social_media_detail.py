from odoo import models, fields, api


class SocialMediaDetail(models.Model):
    _name = 'social.media.detail'
    _rec_name = 'name'
    _description = 'Tour & Travel - Social Media Detail'

    name = fields.Char('Name')
    type_id = fields.Many2one('res.social.media.type', 'Social Media Type')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    agent_id = fields.Many2one('tt.agent', 'Agent')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    customer_id = fields.Many2one('tt.customer', 'Customer', store=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', store=True)
    active = fields.Boolean('Active', default=True)
