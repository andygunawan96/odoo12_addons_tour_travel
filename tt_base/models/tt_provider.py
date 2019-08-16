from odoo import api, fields, models, _


class TtProvider(models.Model):
    _name = 'tt.provider'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    alias = fields.Char(string='Alias')
    code = fields.Char('Code', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    provider_ledger_ids = fields.One2many('tt.provider.ledger', 'provider_id', 'Vendor Ledgers')
    currency_id = fields.Many2one('res.currency', 'Currency')
    provider_code_ids = fields.One2many('tt.provider.code', 'provider_id', 'Provider Codes')
    rate_ids = fields.One2many('tt.provider.rate', 'provider_id', 'Provider Codes')
    payment_acquirer_ids = fields.One2many('payment.acquirer', 'provider_id', 'Payment Acquirers')
    provider_destination_ids = fields.One2many('tt.provider.destination', 'provider_id', 'Destination')
    provider_currency_ids = fields.One2many('tt.provider.currency', 'provider_id', 'Rate(s)')
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
    _description = 'Rodex Model'

    name = fields.Char('Name')
    code = fields.Char('Code')
    # hotel_id = fields.Many2one('tt.hotel', 'Hotel')  # belum ada modulnya
    # facility_id = fields.Many2one('tt.facility', 'Facility')  # belum ada modulnya
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one('res.country.state', 'State')
    city_id = fields.Many2one('res.city', 'City')
    provider_id = fields.Many2one('tt.provider', 'Provider')


class TtProviderDestination(models.Model):
    _name = 'tt.provider.destination'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider', 'Provider')
    country_id = fields.Many2one('res.country', 'Country', required=True)
    is_apply = fields.Boolean('Apply Search', default=True)
    is_all_city = fields.Boolean('Apply to all City', default=True)
    city_ids = fields.One2many('tt.provider.destination.city', 'search_id', 'Cities')


class TtProviderDestinationCity(models.Model):
    _name = 'tt.provider.destination.city'
    _description = 'Rodex Model'

    search_id = fields.Many2one('tt.provider.destination', 'Destination')
    city_id = fields.Many2one('res.city', 'City', required=True)
    is_apply = fields.Boolean('Apply Search', default=False)


class TtProviderCurrency(models.Model):
    _name = 'tt.provider.currency'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider', 'Provider')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    date = fields.Date('Date', default=fields.Date.today())
    buy_rate = fields.Float('Buy Rate', default=1)
    sell_rate = fields.Float('Sell Rate', default=1)
    state = fields.Selection([('draft','Draft'), ('confirm','Active'), ('cancel','Cancelled')])


class TtProviderLedger(models.Model):
    _name = 'tt.provider.ledger'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider', 'Provider')
