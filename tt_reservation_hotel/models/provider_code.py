from odoo import models, fields, api
from datetime import date, datetime, timedelta


class ProviderCode(models.Model):
    _inherit = "tt.provider.code"

    hotel_id = fields.Many2one('tt.hotel', 'Hotel')
    facility_id = fields.Many2one('tt.hotel.facility', 'Facility')
    type_id = fields.Many2one('tt.hotel.type', 'Type')


class Hotel(models.Model):
    _inherit = "tt.hotel"

    provider_hotel_ids = fields.One2many('tt.provider.code', 'hotel_id', 'Provider External Code')

    def get_provider_code(self, hotel_id, provider_id):
        a = self.env['tt.provider.code'].search([('hotel_id', '=', hotel_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelFacility(models.Model):
    _inherit = "tt.hotel.facility"

    provider_ids = fields.One2many('tt.provider.code', 'facility_id', 'Provider External Code')

    def get_provider_code(self, facility_id, provider_id):
        a = self.env['tt.provider.code'].search([('facility_id', '=', facility_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelType(models.Model):
    _inherit = "tt.hotel.type"

    provider_ids = fields.One2many('tt.provider.code', 'type_id', 'Provider External Code')

    def get_provider_code(self, type_id, provider_id):
        a = self.env['tt.provider.code'].search([('type_id', '=', type_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code
