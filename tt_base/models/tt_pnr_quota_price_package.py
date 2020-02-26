from odoo import api,fields,models

class TtPnrQuotaMasterPackage(models.Model):
    _name = 'tt.pnr.quota.price.package'
    _rec_name = 'name'
    _description = 'Rodex Model PNR Quota Master Data'

    name = fields.Char('Name')
    seq_id = fields.Char('Seq ID',readonly=True)
    available_price_list_ids = fields.Many2many('tt.pnr.quota.price.list',
                                           'tt_pnr_quota_price_package_list_rel',
                                           'price_package_id','price_list_id',
                                           'Available Price List')
    minimum_monthly_quota_id = fields.Many2one('tt.pnr.quota.price.list','Minimum Monthly Quota')
    excess_quota_fee = fields.Monetary('Excess Quota Fee')
    currency_id = fields.Many2one('res.currency', default=lambda self:self.env.user.company_id.currency_id.id)
    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.pnr.quota.price.package')
        return super(TtPnrQuotaMasterPackage, self).create(vals_list)
        
    def to_dict(self):
        price_list = []
        for rec in self.available_price_list_ids:
            price_list.append(rec.to_dict())

        return {
            'name': self.name,
            'excess_quota_fee': self.excess_quota_fee,
            'currency': self.currency_id.name,
            'price_list': price_list
        }