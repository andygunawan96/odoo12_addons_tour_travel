from odoo import api, models, fields
from odoo.exceptions import UserError


class ResCurrency(models.Model):
    _inherit = "res.currency"

    code = fields.Char('Code')
    # rate_ids = fields.One2many('tt.provider.rate', 'currency_id', 'Rates')
    country_ids = fields.One2many('res.country', 'currency_id', 'Countries')
    user_ids = fields.One2many('res.users', 'currency_id', 'Users')
    provider_ids = fields.One2many('tt.provider', 'currency_id', 'Providers')
    active = fields.Boolean('Active')
    decimal_places = fields.Integer('Decimal Places',readonly=False)

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(ResCurrency, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(ResCurrency, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(ResCurrency, self).unlink()

    def get_id(self, currency_code, default_param_idr=False):
        res = self.search([('name', '=', currency_code)])
        if res:
            return res.id
        if default_param_idr:
            return self.env.ref('base.IDR').id
        return False
