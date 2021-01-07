from odoo import models, fields, api
from datetime import date, datetime, timedelta

# TODO remove this part
class ProviderCode(models.Model):
    _inherit = 'tt.provider.code'

    hotel_id = fields.Many2one('tt.hotel', 'Hotel')
    facility_id = fields.Many2one('tt.hotel.facility', 'Facility')
    type_id = fields.Many2one('tt.hotel.type', 'Type')


class Hotel(models.Model):
    _inherit = "tt.hotel"

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]

    provider_hotel_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)

    def get_provider_code(self, hotel_id, provider_id):
        a = self.env['tt.provider.code'].search([('hotel_id', '=', hotel_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelFacility(models.Model):
    _inherit = "tt.hotel.facility"

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]

    provider_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)

    def get_provider_code(self, facility_id, provider_id):
        a = self.env['tt.provider.code'].search([('facility_id', '=', facility_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelType(models.Model):
    _inherit = "tt.hotel.type"

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]
    provider_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)

    def get_provider_code(self, type_id, provider_id):
        a = self.env['tt.provider.code'].search([('type_id', '=', type_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelDestination(models.Model):
    _inherit = "tt.hotel.destination"

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]
    provider_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)

    def get_provider_code(self, type_id, provider_id):
        a = self.env['tt.provider.code'].search([('type_id', '=', type_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code

# class HotelMaster(models.Model):
#     _inherit = "tt.hotel.master"

    # def _get_res_model_domain(self):
    #     return [('res_model', '=', self._name)]
    #
    # provider_hotel_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)
    #
    # def get_provider_code(self, hotel_id, provider_id):
    #     a = self.env['tt.provider.code'].search([('hotel_id', '=', hotel_id), ('provider_id', '=', provider_id)], limit= 1)
    #     return a.code
