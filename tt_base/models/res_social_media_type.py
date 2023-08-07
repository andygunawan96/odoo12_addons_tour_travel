from odoo import models, fields, api
from odoo.exceptions import UserError


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

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 400')
        return super(ResSocialMediaType, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 401')
        return super(ResSocialMediaType, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 402')
        return super(ResSocialMediaType, self).unlink()
