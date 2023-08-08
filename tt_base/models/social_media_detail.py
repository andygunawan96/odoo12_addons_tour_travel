from odoo import models, fields, api


class SocialMediaDetail(models.Model):
    _name = 'social.media.detail'
    _rec_name = 'name'
    _description = 'Tour & Travel - Social Media Detail'

    name = fields.Char('Name')
    type_id = fields.Many2one('res.social.media.type', 'Social Media Type')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent')
    provider_ho_data_id = fields.Many2one('tt.provider.ho.data', string='Provider HO Data')
    customer_id = fields.Many2one('tt.customer', 'Customer', store=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', store=True)
    active = fields.Boolean('Active', default=True)
