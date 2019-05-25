from odoo import models, fields


class ResCurrency(models.Model):
    _inherit = "res.currency"

    active = fields.Boolean('Active')
    code = fields.Char('Code')
    res_rate_ids = fields.One2many('res.rate', 'currency_id', 'Rate')
    country_ids = fields.One2many('res.country', 'currency_id', 'Country')
    user_ids = fields.One2many('res.users', 'currency_id', 'User')
    provider_ids = fields.Char('Provider')

    def get_id(self, currency_code):
        res = self.search([('name', '=', currency_code)])
        if res:
            return res.id
        return False
