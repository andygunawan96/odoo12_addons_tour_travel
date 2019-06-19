from odoo import models, fields, api


class ResRate(models.Model):
    _name = 'res.rate'
    _rec_name = 'currency_id'
    _description = 'Tour & Travel - Rate'

    name = fields.Char()
    provider_id = fields.Many2one('tt.provider', 'Provider')
    date = fields.Date(string="Date", required=False)
    currency_id = fields.Many2one('res.currency', 'Currency')
    buy_rate = fields.Monetary('Buy Rate')
    sell_rate = fields.Monetary('Sell Rate')
    active = fields.Boolean('Active', default=True)
