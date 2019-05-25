from odoo import models, fields, api


class ResSocialMediaType(models.Model):
    _name = 'res.social.media.type'
    _rec_name = 'name'
    _description = 'Tour & Travel - Social Media Type'

    name = fields.Char('Name')
    active = fields.Boolean('Active', default=True)
    logo = fields.Binary('Logo')
    black_logo = fields.Binary('Black Logo')
    white_logo = fields.Binary('White Logo')
    social_media_ids = fields.One2many('social.media.detail', 'type_id', 'Social Media Detail')
