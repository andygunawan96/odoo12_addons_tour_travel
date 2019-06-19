from odoo import models, fields


class ResCurrency(models.Model):
    _inherit = "res.currency"

    code = fields.Char('Code')
    # rate_ids = fields.One2many('res.rate', 'currency_id', 'Rates')
    country_ids = fields.One2many('res.country', 'currency_id', 'Countries')
    user_ids = fields.One2many('res.users', 'currency_id', 'Users')
    provider_ids = fields.One2many('tt.provider', 'currency_id', 'Providers')
    active = fields.Boolean('Active')

    def get_id(self, currency_code):
        res = self.search([('name', '=', currency_code)])
        if res:
            return res.id
        return False
