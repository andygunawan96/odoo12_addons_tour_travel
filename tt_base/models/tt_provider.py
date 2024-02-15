from odoo import api, fields, models
from odoo.exceptions import UserError
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback,json

_logger = logging.getLogger(__name__)


class TtProvider(models.Model):
    _name = 'tt.provider'
    _inherit = 'tt.history'
    _description = 'Provider Model'

    name = fields.Char('Name', required=True)
    alias = fields.Char(string='Alias', compute='', store=False, required=True)
    code = fields.Char('Code', required=False)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    provider_code_ids = fields.One2many('tt.provider.code', 'provider_id', 'Provider Codes') ## yg pakai baru hotel, asumsi code selalu sama untuk semua HO
    currency_id = fields.Many2one('res.currency', 'Currency')
    email = fields.Char(string="Email", required=False, )
    payment_acquirer_ids = fields.One2many('payment.acquirer', 'provider_id', 'Payment Acquirers')
    provider_ho_data_ids = fields.One2many('tt.provider.ho.data', 'provider_id', 'Provider HO Data')
    active = fields.Boolean('Active', default=True)
    track_balance = fields.Boolean('Do balance tracking')
    is_reconcile = fields.Boolean('Can be Reconciled')
    required_last_name_on_retrieve = fields.Boolean('Required LastName on Retrieve', default=False)


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

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 415')
        if not vals.get('code'):
            vals['code'] = vals['name'].lower().replace(' ','_')
        if not vals.get('alias'):
            vals['alias'] = vals['name']
        return super(TtProvider, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 416')
        return super(TtProvider, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager') or not self.env.user.has_group('tt_base.group_provider_level_5'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 417')
        return super(TtProvider, self).unlink()

    # delete after implement
    def compute_all_alias(self):
        all_providers = self.search([('alias', '=', '')])
        for rec in all_providers:
            rec.write({
                'alias': rec.name
            })

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

    def get_provider_list_api(self, data, context):
        try:
            provider_type_obj = self.env['tt.provider.type'].search([('code','=', data['provider_type'])], limit=1)
            provider_objs = self.search([('provider_type_id', '=', provider_type_obj.id)])
            res = []
            for provider_obj in provider_objs:
                res.append({
                    "name": provider_obj.name,
                    "code": provider_obj.code
                })
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return RequestException(500)

    def get_provider_api(self): ## data awal gateway
        res = []
        for rec in self.search([]):
            res.append({
                "name": rec.name,
                "code": rec.code
            })
        return ERR.get_no_error(res)

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

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 418')
        return super(TtProviderCode, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 419')
        return super(TtProviderCode, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 420')
        return super(TtProviderCode, self).unlink()

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

    def find_city_country(self):
        list_name = [self.name.replace(')',''),]
        for params in [';', '(', ',']:
            new_list_name = []
            for part_name in list_name:
                new_list_name += part_name.split(params)
            list_name = new_list_name

        dest_name = list_name[0].strip()
        state_name = ""
        other_name = ""
        country_name = ""
        if len(list_name) > 1:
            country_name = list_name[-1].strip()

        # Example [100 Mile House, Bc, Canada]
        # Part tengah bisa berarti State bisa jdi country Code
        if len(list_name) > 2:
            state_name = list_name[1].strip()
        if len(list_name) == 4:
            other_name = list_name[2].strip()

        # Cek City
        country_obj = self.env['res.country'].find_country_by_name(country_name, 1)
        city_objs = self.env['res.city'].find_city_by_name(dest_name, country_id=country_obj.id, limit=100)

        # Jika result city by country lebih dri 1 cek ulng by state / other
        if len(city_objs.ids) == 1:
            self.city_id = city_objs.ids[0]
            self.format_new()
            return True
        elif len(city_objs.ids):
            state_strs = [state_name, other_name]
            state_ids = []
            state_obj = self.env['res.country.state'].find_state_by_name(state_name, country_id=country_obj.id, limit=1)
            if state_obj:
                state_strs += [state_obj.name, state_obj.code]
                state_ids.append(state_obj.id)
            other_obj = self.env['res.country.state'].find_state_by_name(other_name, country_id=country_obj.id, limit=1)
            if other_obj:
                state_strs += [other_obj.name, other_obj.code]
                state_ids.append(other_obj.id)
            for city_obj in city_objs:
                if city_obj.state_id and city_obj.state_id.id in state_ids or city_obj.state_id.code in state_strs:
                    self.city_id = city_obj.id
                    self.format_new()
                    return True

        # Cek tt_hotel_Destinasi => Inherit
        return {
            'id': False,
            'name': self.name,
            'city_str': dest_name,
            'state_str': state_name,
            'country_id': country_obj.id,
            'country_str': country_name,
        }

    def clear_all(self):
        for rec in self:
            rec.country_id = False
            rec.state_id = False
            rec.city_id = False
            rec.res_model = False
            rec.res_id = False


class TtProviderDestination(models.Model):
    _name = 'tt.provider.destination'
    _description = 'Provider Destination'

    provider_ho_data_id = fields.Many2one('tt.provider.ho.data', 'Provider HO Data')
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

    provider_ho_data_id = fields.Many2one('tt.provider.ho.data', 'Provider HO Data')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    date = fields.Date('Date', default=fields.Date.today())
    buy_rate = fields.Float('Buy Rate', default=1)
    sell_rate = fields.Float('Sell Rate', default=1)
    state = fields.Selection([('draft','Draft'), ('confirm','Active'), ('cancel','Cancelled')])


class TtProviderLedger(models.Model):
    _name = 'tt.provider.ledger'
    _description = 'Provider Balance Ledger'
    _order = 'id DESC'

    provider_ho_data_id = fields.Many2one('tt.provider.ho.data', 'Provider HO Data')
    currency_id = fields.Many2one('res.currency',related='provider_ho_data_id.currency_id')
    balance = fields.Monetary('Balance')

class TtProviderHOData(models.Model):
    _name = 'tt.provider.ho.data'
    _inherit = 'tt.history'
    _description = 'Provider Head Office Data'
    _order = 'id DESC'

    name = fields.Char('Name')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', related='provider_id.provider_type_id', readonly=True)

    provider_ledger_ids = fields.One2many('tt.provider.ledger', 'provider_ho_data_id', 'Vendor Ledgers')
    currency_id = fields.Many2one('res.currency', 'Currency')
    address_ids = fields.One2many('address.detail', 'provider_ho_data_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'provider_ho_data_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'provider_ho_data_id', 'Social Media')
    rate_ids = fields.One2many('tt.provider.rate', 'provider_ho_data_id', 'Provider Codes')

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id)
    balance = fields.Monetary('Balance', related="provider_ledger_ids.balance")
    provider_destination_ids = fields.One2many('tt.provider.destination', 'provider_ho_data_id', 'Destination')

    provider_currency_ids = fields.One2many('tt.provider.currency', 'provider_ho_data_id', 'Rate(s)')
    is_using_balance = fields.Boolean('Is Using Balance')
    is_using_lg = fields.Boolean('Is Using Letter of Guarantee')
    is_using_po = fields.Boolean('Is Using Purchase Order')
    active = fields.Boolean('Active', default=True)

    def sync_balance(self, agent_obj=False):
        ##send request to gateway
        ho_id = self.ho_id.id
        get_vendor_balance_dict = self.env['tt.%s.api.con' % (self.provider_id.provider_type_id.code)].get_balance(self, self.provider_id.code, ho_id)
        if get_vendor_balance_dict['error_code'] == 0:
            self.create_provider_ledger(get_vendor_balance_dict['response']['balance'])
        else:
            _logger.error(json.dumps(get_vendor_balance_dict))
            raise UserError('%s' % get_vendor_balance_dict['error_msg'])


    def create_provider_ledger(self,balance):
        self.env['tt.provider.ledger'].sudo().create({
            'balance': balance,
            'provider_ho_data_id': self.id,
        })

    def create_provider_ledger_api(self,data,context):
        try:
            dom = []
            if context.get('co_ho_id'):
                dom.append(('ho_id','=', context['co_ho_id']))
            if 'rodextrip' in data['provider_code']: #asumsi hard code kalau provider rodextrip_x maka di masukkan rodextrip airline semua biar 1 saldo
                dom.append(('provider_id.code', '=', 'rodextrip_airline'))
                provider_obj = self.search(dom, limit=1)
            else:
                dom.append(('provider_id.code','=',data['provider_code']))
                provider_obj = self.search(dom, limit=1)
            if provider_obj:
                provider_obj.create_provider_ledger(data['balance'])
            else:
                provider = data['provider_code']
                if 'rodextrip' in provider:
                    provider = 'rodextrip_airline'
                ho_name = ''
                if context.get('co_ho_id'):
                    ho_name = self.env['tt.agent'].browse(context['co_ho_id']).name
                _logger.error("Please add Provider HO Data %s for HO %s" % (provider, ho_name))
                raise RequestException(1002)
        except:
            _logger.error(traceback.format_exc())
            return Exception("Create Provider Ledger Failed")
        return ERR.get_no_error()

    def get_vendor_balance_api(self,context):
        try:
            provider_obj = self.search([('ho_id', '=', context['co_ho_id']), ('provider_id.track_balance','=', True)])
            res = []
            for rec in provider_obj:
                code_name = 'rodextrip' if 'rodextrip' in rec.provider_id.code else rec.provider_id.code
                provider_values = {
                    "code": code_name.capitalize(),
                    "provider_type": rec.provider_id.provider_type_id.code,
                    "balance": rec.balance,
                    "currency": rec.currency_id and rec.currency_id.name or ''
                }
                res.append(provider_values)
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return RequestException(500)



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
        city_id = self.find_city_by_name(city_name)
        if not city_id:
            city_id = self.create({'name': city_name, 'state_id': state_id, 'country_id': country_id})
        else:
            city_id = city_id[0]
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
        country_id = self.find_country_by_name(country_name)
        if not country_id:
            # TODO: Persiapan Continent disini
            country_id = self.create({'name': country_name,})
        else:
            country_id = country_id[0]
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
