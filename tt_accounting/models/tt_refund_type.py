from odoo import api,models,fields,_
from odoo.exceptions import UserError


class TtRefundType(models.Model):
    _name = "tt.refund.type"
    _inherit = 'tt.history'
    _description = "Refund Type Model"

    name = fields.Char('Name', default='New')
    days = fields.Integer('Amount of Days', default=40)
    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 376')
        return super(TtRefundType, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 377')
        return super(TtRefundType, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 378')
        return super(TtRefundType, self).unlink()
