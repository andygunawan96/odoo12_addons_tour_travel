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


class Hotel(models.Model):
    _inherit = "tt.hotel"

    provider_hotel_ids = fields.One2many('provider.code', 'hotel_id', 'Provider External Code')

    def get_provider_code(self, hotel_id, provider_id):
        a = self.env['tt.provider.code'].search([('hotel_id', '=', hotel_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelFacility(models.Model):
    _inherit = "tt.hotel.facility"

    provider_ids = fields.One2many('provider.code', 'facility_id', 'Provider External Code')

    def get_provider_code(self, facility_id, provider_id):
        a = self.env['tt.provider.code'].search([('facility_id', '=', facility_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelType(models.Model):
    _inherit = "tt.hotel.type"

    provider_ids = fields.One2many('provider.code', 'type_id', 'Provider External Code')

    def get_provider_code(self, type_id, provider_id):
        a = self.env['tt.provider.code'].search([('type_id', '=', type_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code
