from odoo import api,fields,models

PRICE_TYPE = [
    ('pnr', 'PNR'),
    ('r/n', 'R/N'),
    ('pax', 'Passenger'),
    ('pnr/pax', 'PNR/PAX')
]

class TtPnrQuotaPriceList(models.Model):
    _name = 'tt.pnr.quota.price.list'
    _rec_name = 'name'
    _description = 'PNR Quota Price List'

    def get_domain_provider(self):
        if self.provider_type_id:
            domain_id = self.env.ref('tt_reservation_%s.tt_provider_type_%s' % (self.provider_type_id.code, self.provider_type_id.code)).id
            return [('provider_type_id.id', '=', int(domain_id))]
        else:
            return []

    def get_domain_carrier(self):
        if self.provider_type_id:
            domain_id = self.env.ref('tt_reservation_%s.tt_provider_type_%s' % (self.provider_type_id.code, self.provider_type_id.code)).id
            return [('provider_type_id', '=', int(domain_id))]
        else:
            return []

    name = fields.Char('Name')
    seq_id = fields.Char('Sequence ID', readonly=True)
    price_type = fields.Selection(PRICE_TYPE, 'Price Type')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain_provider)
    provider_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Provider Type Access Type', default='all')


    carrier_id = fields.Many2one('tt.transport.carrier', 'Carrier Code', domain=get_domain_carrier)
    carrier_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],
                                                 'Carrier Access Type', default='all')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self:self.env.user.company_id.currency_id.id)
    price = fields.Monetary('Price')
    active = fields.Boolean('Active', default=True)
    used_package_list_ids = fields.Many2many('tt.pnr.quota.price.package',
                                           'tt_pnr_quota_price_package_list_rel',
                                           'price_list_id','price_package_id',
                                           'Used in Package List')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.pnr.quota.price.list')
        return super(TtPnrQuotaPriceList, self).create(vals_list)

    def to_dict(self):
        return {
            'seq_id': self.seq_id,
            'name': self.name,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'price': self.price,
        }
