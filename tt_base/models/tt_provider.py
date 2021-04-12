from odoo import api, fields, models
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback

_logger = logging.getLogger(__name__)


class TtProvider(models.Model):
    _name = 'tt.provider'
    _inherit = 'tt.history'
    _description = 'Provider Model'

    name = fields.Char('Name', required=True)
    alias = fields.Char(string='Alias')
    code = fields.Char('Code', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    provider_ledger_ids = fields.One2many('tt.provider.ledger', 'provider_id', 'Vendor Ledgers')
    email = fields.Char(string="Email", required=False, )
    currency_id = fields.Many2one('res.currency', 'Currency')
    address_ids = fields.One2many('address.detail', 'provider_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'provider_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'provider_id', 'Social Media')
    provider_code_ids = fields.One2many('tt.provider.code', 'provider_id', 'Provider Codes')
    rate_ids = fields.One2many('tt.provider.rate', 'provider_id', 'Provider Codes')
    payment_acquirer_ids = fields.One2many('payment.acquirer', 'provider_id', 'Payment Acquirers')
    provider_destination_ids = fields.One2many('tt.provider.destination', 'provider_id', 'Destination')
    provider_currency_ids = fields.One2many('tt.provider.currency', 'provider_id', 'Rate(s)')
    active = fields.Boolean('Active', default=True)
    balance = fields.Monetary('Balance', related="provider_ledger_ids.balance")
    track_balance = fields.Boolean('Do balance tracking')
    is_reconcile = fields.Boolean('Can be Reconciled')
    is_using_balance = fields.Boolean('Is Using Balance')
    is_using_lg = fields.Boolean('Is Using Letter of Guarantee')
    is_using_po = fields.Boolean('Is Using Purchase Order')

    #kasus concurrent update
    # def sync_balance(self):
    #     ##send request to gateway
    #     #_send_request('sia')
    #     if self.track_balance:
    #         self.sudo().write({
    #             'provider_ledger_ids': [(0,0,{
    #                 'balance': self.env['tt.%s.api.con' % (self.provider_type_id.code)].get_balance(self.code)['response']['balance'],
    #                 'provider_id': self.id
    #             })]
    #         })

    def sync_balance(self):
        ##send request to gateway
        self.create_provider_ledger(self.env['tt.%s.api.con' % (self.provider_type_id.code)].get_balance(self.code)['response']['balance'])


    def create_provider_ledger(self,balance):
        self.env['tt.provider.ledger'].sudo().create({
                'balance': balance,
                'provider_id': self.id
            })

    def create_provider_ledger_api(self,data,context):
        try:
            provider_obj = self.search([('code','=',data['provider_code'])], limit=1)
            if provider_obj:
                provider_obj.create_provider_ledger(data['balance'])
            else:
                raise RequestException(1002)
        except:
            _logger.error(traceback.format_exc())
            return Exception("Create Provider Ledger Failed")
        return ERR.get_no_error()

    def to_dict(self):
        return {
            'name': self.name,
            'alias': self.alias,
            'code': self.code,
            'provider_type_id': self.provider_type_id.id
        }

    def get_data(self):
        return {
            'name': self.name,
            'alias': self.alias,
            'code': self.code,
        }

    ### code = string , provider_type = object
    def get_provider_id(self,code,provider_type):
        provider_obj = self.search([('code','=',code),('provider_type_id','=',provider_type.id)], limit=1)
        return provider_obj.id

    def clear_destination_ids(self):
        for rec in self:
            rec.provider_destination_ids = False

    def compute_destination_ids(self):
        for rec in self:
            for country in self.env['res.country'].search([]):
                self.env['tt.provider.destination'].create({
                    'provider_id': rec.id,
                    'country_id': country.id,
                })

    def get_vendor_balance_api(self,context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        if user_obj.agent_id.id == self.env.ref('tt_base.rodex_ho').id:
            provider_obj = self.search([('track_balance', '=', True)])
            res = []
            for rec in provider_obj:
                res.append({
                    "code": rec.code,
                    "provider_type": rec.provider_type_id.code,
                    "balance": rec.balance,
                    "currency": rec.currency_id.name
                })
            return ERR.get_no_error(res)
        else:
            raise RequestException(500)

class TtProviderCode(models.Model):
    _name = 'tt.provider.code'
    _description = 'Provider Code Model'

    name = fields.Char('Name')
    code = fields.Char('Code')
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one('res.country.state', 'State')
    city_id = fields.Many2one('res.city', 'City')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',related='provider_id.provider_type_id',store=True)

    res_model = fields.Char('Related Reservation Name', index=True, readonly=False)
    res_id = fields.Integer('Related Reservation ID', index=True, help='ID of the followed resource', readonly=False)

    def open_record(self, rec_id):
        try:
            form_id = self.env[self.rec_model].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model,
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def open_record_parent(self):
        return self.open_record(self.res_id)

    # Temporary function untuk rubah ke format baru
    def format_new(self):
        rec = self
        if rec.country_id:
            rec.res_id = rec.country_id.id
            rec.res_model = 'res.country'
        elif rec.state_id:
            rec.res_id = rec.state_id.id
            rec.res_model = 'res.country.state'
        elif rec.city_id:
            rec.res_id = rec.city_id.id
            rec.res_model = 'res.city'
        elif rec.hotel_id:
            rec.res_id = rec.hotel_id.id
            rec.res_model = 'tt.hotel'
        elif rec.facility_id:
            rec.res_id = rec.facility_id.id
            rec.res_model = 'tt.hotel.facility'
        elif rec.type_id:
            rec.res_id = rec.type_id.id
            rec.res_model = 'tt.hotel.type'

    # function untuk rubah dari res_model res_id ke city_id / state_id / country_id
    def format_old(self):
        rec = self
        if rec.res_model == 'res.country':
            rec.country_id = rec.res_id
        elif rec.res_model == 'res.country.state':
            rec.state_id = rec.res_id
        elif rec.res_model == 'res.city':
            rec.city_id = rec.res_id
        elif rec.res_model == 'tt.hotel':
            rec.hotel_id = rec.res_id
        elif rec.res_model == 'tt.hotel.facility':
            rec.facility_id = rec.res_id
        elif rec.res_model == 'tt.hotel.type':
            rec.type_id = rec.res_id


class TtProviderDestination(models.Model):
    _name = 'tt.provider.destination'
    _description = 'Provider Destination'

    provider_id = fields.Many2one('tt.provider', 'Provider')
    country_id = fields.Many2one('res.country', 'Country', required=True)
    is_apply = fields.Boolean('Apply Search', default=True)
    is_all_city = fields.Boolean('Apply to all City', default=True)
    city_ids = fields.One2many('tt.provider.destination.city', 'search_id', 'Cities')


class TtProviderDestinationCity(models.Model):
    _name = 'tt.provider.destination.city'
    _description = 'Provider Destination City'

    search_id = fields.Many2one('tt.provider.destination', 'Destination')
    city_id = fields.Many2one('res.city', 'City', required=True)
    is_apply = fields.Boolean('Apply Search', default=False)


class TtProviderCurrency(models.Model):
    _name = 'tt.provider.currency'
    _description = 'Provider Currency'

    provider_id = fields.Many2one('tt.provider', 'Provider')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    date = fields.Date('Date', default=fields.Date.today())
    buy_rate = fields.Float('Buy Rate', default=1)
    sell_rate = fields.Float('Sell Rate', default=1)
    state = fields.Selection([('draft','Draft'), ('confirm','Active'), ('cancel','Cancelled')])


class TtProviderLedger(models.Model):
    _name = 'tt.provider.ledger'
    _description = 'Provider Balance Ledger'
    _order = 'id DESC'

    provider_id = fields.Many2one('tt.provider', 'Provider')
    currency_id = fields.Many2one('res.currency',related='provider_id.currency_id')
    balance = fields.Monetary('Balance')

class ResCity(models.Model):
    _inherit = "res.city"

    provider_city_ids = fields.One2many('tt.provider.code', 'city_id', 'Provider External Code')
    image_url = fields.Char('City Icon', help='resolution in 200x200')

    def get_provider_code(self, city_id, provider_id):
        if provider_id == self.env.ref('tt_reservation_hotel.tt_hotel_provider_rodextrip_hotel').id:
            try:
                return self.env['res.city'].browse(city_id).name.title()
            except:
                pass

        a = self.env['tt.provider.code'].sudo().search([('city_id', '=', city_id), ('provider_id', '=', provider_id)], limit=1)
        if not a: # New Format
            a = self.env['tt.provider.code'].sudo().search([('res_model', '=', 'res.city'), ('res_id', '=', city_id), ('provider_id', '=', provider_id)], limit=1)
        return a.code

    def get_city_country_provider_code(self, city_id, provider_code):
        provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider_code)], limit=1).id
        a = self.get_provider_code(city_id, provider_id)
        country_id = self.browse(city_id).country_id.id
        b = self.env['res.country'].get_provider_code(country_id, provider_id)
        return {'city_id': a, 'country_id': b}

    def update_provider_data(self, city_name, provider_uid, provider_id, state_id=False, country_id=False):
        city_id = self.search([('name', '=ilike', city_name)], limit=1)
        if not city_id:
            city_id = self.create({'name': city_name, 'state_id': state_id, 'country_id': country_id})
        provider_code_id = self.env['tt.provider.code'].search([('city_id', '=', city_id.id), ('provider_id', '=', provider_id)], limit=1)
        if provider_code_id:
            provider_code_id.code = provider_uid
        else:
            self.env['tt.provider.code'].create({
                'code': provider_uid,
                'provider_id': provider_id,
                'city_id': city_id.id,
            })
        return city_id.id


class ResCountry(models.Model):
    _inherit = "res.country"

    provider_city_ids = fields.One2many('tt.provider.code', 'country_id', 'Provider External Code')

    def get_provider_code(self, country_id, provider_id):
        a = self.env['tt.provider.code'].search([('country_id', '=', country_id), ('provider_id', '=', provider_id)], limit= 1)
        if not a: # New Format
            a = self.env['tt.provider.code'].sudo().search([('res_model', '=', 'res.country'), ('res_id', '=', country_id), ('provider_id', '=', provider_id)], limit=1)
        return a.code

    def update_provider_data(self, country_name, provider_uid, provider_id, continent_id=False):
        country_id = self.search([('name', '=ilike', country_name)], limit=1)
        if not country_id:
            # TODO: Persiapan Continent disini
            country_id = self.create({'name': country_name,})
        # if country_id.id == 101:
        #     pass
        provider_code_id = self.env['tt.provider.code'].search([('country_id', '=', country_id.id), ('provider_id', '=', provider_id)], limit= 1)
        if provider_code_id:
            provider_code_id.code = provider_uid
        else:
            self.env['tt.provider.code'].create({
                'code': provider_uid,
                'provider_id': provider_id,
                'country_id': country_id.id,
            })
        return country_id.id

    def get_all_countries(self):
        countries = self.search([])
        data = []
        for country in countries:
            json = {
                'id': country.id,
                'type': 'country',
                'name': country.name,
                'display_name': country.name,
                'provider': {},
            }
            for provider in country.provider_city_ids:
                json['provider'].update({
                    str(
                        provider.provider_id.provider_code and provider.provider_id.provider_code or provider.provider_id.name).lower(): provider.code,
                })
            data.append(json)
        return data


class CountryState(models.Model):
    _inherit = 'res.country.state'

    provider_state_ids = fields.One2many('tt.provider.code', 'state_id', 'Provider External Code')
    code = fields.Char(string='State Code', required=False)

    def get_provider_code(self, state_id, provider_id):
        a = self.env['tt.provider.code'].sudo().search([('state_id', '=', state_id.id), ('provider_id', '=', provider_id)], limit=1)
        return a.code

    def get_city_country_provider_code(self, state_id, provider_code):
        provider_id = self.env['res.partner'].sudo().search([('provider_code', '=', provider_code)]).id
        # provider_id = self.env['tt.master.vendor'].sudo().search([('provider', '=', provider_code)]).id
        a = self.get_provider_code(state_id, provider_id)
        country_id = self.browse(state_id).country_id.id
        b = self.env['res.country'].get_provider_code(country_id, provider_id)
        return {'city_id': a, 'country_id': b}

    def update_provider_data(self, state_name, provider_uid, provider_id, country_id=False):
        state_id = self.search([('name', '=', state_name)], limit=1)
        if not state_id:
            try:
                state_id = self.create({'name': state_name, 'country_id': country_id})
            except Exception as e:
                state_id = self.create({'name': state_name, 'country_id': country_id})
        provider_code_id = self.env['tt.provider.code'].search([('state_id', '=', state_id.id), ('provider_id', '=', provider_id)], limit= 1)
        if provider_code_id:
            provider_code_id.code = provider_uid
        else:
            self.env['tt.provider.code'].create({
                'code': provider_uid,
                'provider_id': provider_id,
                'state_id': state_id.id,
            })
        return state_id.id
