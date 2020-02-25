from odoo import api,fields,models

class TtPnrQuotaMasterData(models.Model):
    _name = 'tt.pnr.quota.price.list'
    _rec_name = 'name'
    _description = 'Rodex Model PNR Quota Master Data'

    name = fields.Char('Name')
    amount = fields.Integer('Amount')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self:self.env.user.company_id.currency_id)
    price = fields.Monetary('Price')
    active = fields.Boolean('Active', default=True)
