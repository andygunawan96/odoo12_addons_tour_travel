from odoo import models, fields, api
from datetime import date, datetime, timedelta


class ProviderCode(models.Model):
    _inherit = "tt.provider.code"

    hotel_id = fields.Many2one('tt.hotel', 'Hotel')
    facility_id = fields.Many2one('tt.hotel.facility', 'Facility')
    type_id = fields.Many2one('tt.hotel.type', 'Type')
    confidence = fields.Float('Confidence', help='1(Lowest) - 5 (Highest)')

    def find_city_by_string(self, part_name, result_data, value1=1, value2=0):
        result = self.env['res.country'].search([('name', '=ilike', part_name)], limit=1)
        if result:
            result_data['country'].update({part_name: [result[0].id, value1]})
        else:
            result = self.env['res.country'].search([('other_name_ids', 'ilike', part_name)])
            if result:
                result_data['country'].update({part_name: [result[0].id, value2]})
            else:
                result_data['country'].update({part_name: [False, 0]})

        result = self.env['res.city'].search([('name', '=ilike', part_name)], limit=1)
        if result:
            result_data['city'].update({part_name: [result[0].id, value1]})
        else:
            result = self.env['res.city'].search([('city_alias_name', 'ilike', part_name)])
            if result:
                result_data['city'].update({part_name: [result[0].id, value2]})
            else:
                result_data['city'].update({part_name: [False, 0]})
        return result_data

    def is_result_empty(self, result_data):
        for rec in result_data['country'].keys():
            if result_data['country'][rec][0] != False:
                return False

        for rec in result_data['city'].keys():
            if result_data['city'][rec][0] != False:
                return False
        return True

    def find_city_country(self):
        for rec in self.search([('id', '>', self.id), ('country_id', '=', False), ('city_id', '=', False)], limit=8000):
            result_data = {
                'country': {},
                'city': {}
            }
            part_names = rec.name.split(',')[0].replace('-', ' ').replace('(', '').replace(')', '')
            result_data = self.find_city_by_string(part_names, result_data, 5, 4)

            if self.is_result_empty(result_data):
                part_names = part_names.split(' ')
                for part_name in part_names:
                    result_data = self.find_city_by_string(part_name, result_data, 4, 3)
            else:
                part_names = [part_names, ]

            # ReCheck hasil nya
            total_country = 0
            total_city = 0
            for part_name in part_names:
                total_country += result_data['country'][part_name][1]
                total_city += result_data['city'][part_name][1]
            if total_country > total_city:
                rec.country_id = result_data['country'][part_names[0]][0]
                rec.confidence = total_country/len(part_names)
            else:
                rec.city_id = result_data['city'][part_names[0]][0]
                rec.confidence = total_city/len(part_names)

    def clear_rel(self):
        for rec in self.search(['|', ('country_id', '!=', False), ('city_id', '!=', False)]):
            rec.country_id = False
            rec.city_id = False


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
