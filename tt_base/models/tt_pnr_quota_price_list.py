from odoo import api,fields,models

class TtPnrQuotaMasterData(models.Model):
    _name = 'tt.pnr.quota.price.list'
    _rec_name = 'name'
    _description = 'Rodex Model PNR Quota Master Data'

    name = fields.Char('Name')
    seq_id = fields.Char('Seq ID', readonly=True)
    amount = fields.Integer('Amount')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self:self.env.user.company_id.currency_id)
    price = fields.Monetary('Price')
    active = fields.Boolean('Active', default=True)
    validity_duration = fields.Integer('Validity Duration (days)', default=30)
    used_package_list_ids = fields.Many2many('tt.pnr.quota.price.package',
                                           'tt_pnr_quota_price_package_list_rel',
                                           'price_list_id','price_package_id',
                                           'Used in Package List')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.pnr.quota.price.list')
        return super(TtPnrQuotaMasterData, self).create(vals_list)

    def to_dict(self):
        return {
            'name': self.name,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'price': self.price,
            'validity_duration': self.validity_durations
        }
