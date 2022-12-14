from odoo import api,fields,models

class TtPnrQuotaPricePackage(models.Model):
    _name = 'tt.pnr.quota.price.package'
    _rec_name = 'name'
    _description = 'PNR Quota Price Package'

    name = fields.Char('Name')
    seq_id = fields.Char('Sequence ID',readonly=True)
    available_price_list_ids = fields.Many2many('tt.pnr.quota.price.list',
                                           'tt_pnr_quota_price_package_list_rel',
                                           'price_package_id','price_list_id',
                                           'Available Price List')
    minimum_fee = fields.Monetary('Minimum Fee',default=0)
    validity = fields.Integer('Validity Month', default=1)
    free_usage = fields.Integer('Free Usage', default=1000)
    fix_profit_share = fields.Boolean('Fix Profit Share', default=True, help="""Check to ignore internal inventory""")
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self:self.env.user.company_id.currency_id.id)
    active = fields.Boolean('Active', default=True)
    is_calculate_all_inventory = fields.Boolean('Is count internal inventory', default=False, help="""to calculate all inventory""")

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.pnr.quota.price.package')
        return super(TtPnrQuotaPricePackage, self).create(vals_list)
        
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