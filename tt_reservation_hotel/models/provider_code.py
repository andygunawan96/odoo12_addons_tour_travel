from odoo import models, fields, api
from datetime import date, datetime, timedelta


class ProviderCode(models.Model):
    _name = "provider.code"

    # @api.onchange('provider_id', 'city_id')
    # @api.onchange('city_id', 'country_id')
    # @api.multi
    # def _get_default_name(self):
    #     for a in self:
    #         a.name = ''
    #         # a.name += a.provider_id and a.provider_id + ' ' or ''
    #         a.name += a.country_id and a.country_id.name + ' ' or ''
    #         a.name += a.city_id and a.city_id.name or ''

    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one('res.country.state', 'State')
    city_id = fields.Many2one('res.city', 'City')
    # district_id = fields.Many2one('res.country.district', 'District')
    hotel_id = fields.Many2one('tt.hotel', 'Hotel')
    facility_id = fields.Many2one('tt.hotel.facility', 'Facility')
    type_id = fields.Many2one('tt.hotel.type', 'Type')
    # provider_id = fields.Integer('Provider')
    provider_id = fields.Many2one('res.partner', 'Provider', domain="[('is_vendor', '=', 'vendor'), ('parent_id', '=', False)]")
    # provider_id = fields.Many2one('tt.master.vendor', 'Provider')
    code = fields.Char('Code')
    name = fields.Char('Name')


class ResCity(models.Model):
    _inherit = "res.city"

    provider_city_ids = fields.One2many('provider.code', 'city_id', 'Provider External Code')
    image_url = fields.Char('City Icon', help='resolution in 200x200')

    def get_provider_code(self, city_id, provider_id):
        a = self.env['provider.code'].sudo().search([('city_id', '=', city_id), ('provider_id', '=', provider_id)], limit=1)
        return a.code

    def get_city_country_provider_code(self, city_id, provider_code):
        provider_id = self.env['res.partner'].sudo().search([('provider_code', '=', provider_code)], limit=1).id
        # provider_id = self.env['tt.master.vendor'].sudo().search([('provider', '=', provider_code)]).id
        a = self.get_provider_code(city_id, provider_id)
        country_id = self.browse(city_id).country_id.id
        b = self.env['res.country'].get_provider_code(country_id, provider_id)
        return {'city_id': a, 'country_id': b}

    def update_provider_data(self, city_name, provider_uid, provider_id, state_id=False):
        city_id = self.search([('name', '=', city_name)], limit=1)
        if not city_id:
            city_id = self.create({'name': city_name, 'state_id': state_id,})
        provider_code_id = self.env['provider.code'].search([('city_id', '=', city_id.id), ('provider_id', '=', provider_id)], limit= 1)
        if provider_code_id:
            provider_code_id.code = provider_uid
        else:
            self.env['provider.code'].create({
                'code': provider_uid,
                'provider_id': provider_id,
                'city_id': city_id.id,
            })
        return city_id.id


class ResCountry(models.Model):
    _inherit = "res.country"

    provider_city_ids = fields.One2many('provider.code', 'country_id', 'Provider External Code')

    def get_provider_code(self, country_id, provider_id):
        a = self.env['provider.code'].search([('country_id', '=', country_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code

    def update_provider_data(self, country_name, provider_uid, provider_id, continent_id=False):
        country_id = self.search([('name', '=', country_name)], limit=1)
        if not country_id:
            # TODO: Persiapan Continent disini
            country_id = self.create({'name': country_name,})
        if country_id.id == 101:
            pass
        provider_code_id = self.env['provider.code'].search([('country_id', '=', country_id.id), ('provider_id', '=', provider_id)], limit= 1)
        if provider_code_id:
            provider_code_id.code = provider_uid
        else:
            self.env['provider.code'].create({
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

    provider_state_ids = fields.One2many('provider.code', 'state_id', 'Provider External Code')
    code = fields.Char(string='State Code', required=False)

    def get_provider_code(self, state_id, provider_id):
        a = self.env['provider.code'].sudo().search([('state_id', '=', state_id.id), ('provider_id', '=', provider_id)], limit=1)
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
                state_id = self.create({'name': state_name, 'country_id': country_id, })
                # state_id = self.create({'name': state_name, 'country_id': country_id, 'code': str(provider_id) + '_' + str(country_id) + '_' + state_name[:2] + state_name[-2:],})
            except:
                state_id = self.create({'name': state_name, 'country_id': country_id,})
        provider_code_id = self.env['provider.code'].search([('state_id', '=', state_id.id), ('provider_id', '=', provider_id)], limit= 1)
        if provider_code_id:
            provider_code_id.code = provider_uid
        else:
            self.env['provider.code'].create({
                'code': provider_uid,
                'provider_id': provider_id,
                'state_id': state_id.id,
            })
        return state_id.id


class Hotel(models.Model):
    _inherit = "tt.hotel"

    provider_hotel_ids = fields.One2many('provider.code', 'hotel_id', 'Provider External Code')

    def get_provider_code(self, hotel_id, provider_id):
        a = self.env['provider.code'].search([('hotel_id', '=', hotel_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelFacility(models.Model):
    _inherit = "tt.hotel.facility"

    provider_ids = fields.One2many('provider.code', 'facility_id', 'Provider External Code')

    def get_provider_code(self, facility_id, provider_id):
        a = self.env['provider.code'].search([('facility_id', '=', facility_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelType(models.Model):
    _inherit = "tt.hotel.type"

    provider_ids = fields.One2many('provider.code', 'type_id', 'Provider External Code')

    def get_provider_code(self, type_id, provider_id):
        a = self.env['provider.code'].search([('type_id', '=', type_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code
