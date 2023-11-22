from odoo import api,models,fields


class IrExportsInh(models.Model):
    _inherit = "ir.exports"

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)],
                            default=lambda self: self.env.user.ho_id)
