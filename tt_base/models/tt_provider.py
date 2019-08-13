from odoo import api, fields, models, _


class TtProvider(models.Model):
    _name = 'tt.provider'

    name = fields.Char('Name', required=True)
    alias = fields.Char(string='Alias')
    code = fields.Char('Code', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    vendor_ledger_ids = fields.One2many('tt.vendor.ledger', 'provider_id', 'Vendor Ledgers')
    currency_id = fields.Many2one('res.currency', 'Currency')
    provider_code_ids = fields.One2many('tt.provider.code', 'provider_id', 'Provider Codes')
    rate_ids = fields.One2many('res.rate', 'provider_id', 'Provider Codes')
    payment_acquirer_ids = fields.One2many('payment.acquirer', 'provider_id', 'Payment Acquirers')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        return {
            'name': self.name,
            'alias': self.alias,
            'code': self.code,
            'provider_type_id': self.provider_type_id.id
        }

    ### code = string , provider_type = object
    def get_provider_id(self,code,provider_type):
        provider_obj = self.search([('code','=',code),('provider_type_id','=',provider_type.id)])
        return provider_obj.id


class TtProviderCode(models.Model):
    _name = 'tt.provider.code'

    name = fields.Char('Name')
    code = fields.Char('Code')
    # hotel_id = fields.Many2one('tt.hotel', 'Hotel')  # belum ada modulnya
    # facility_id = fields.Many2one('tt.facility', 'Facility')  # belum ada modulnya
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one('res.country.state', 'State')
    city_id = fields.Many2one('res.city', 'City')
    provider_id = fields.Many2one('tt.provider', 'Provider')


class TtVendorLedger(models.Model):
    _name = 'tt.vendor.ledger'

    provider_id = fields.Many2one('tt.provider', 'Provider')
