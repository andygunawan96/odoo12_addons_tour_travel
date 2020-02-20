from odoo import api,fields,models

class TtPnrQuotaMasterData(models.Model):
    _name = 'tt.pnr.quota.price.list'
    _rec_name = 'name'
    _description = 'Rodex Model PNR Quota Master Data'

    name = fields.Char('Name')
    price = fields.Monetary('Price')
    currency_id = fields.Many2one('res.currency',default=lambda self:self.env.user.company_id.currency_id.id)
