from odoo import models, fields, api
from datetime import date, datetime, timedelta


class CityType(models.Model):
    _name = 'res.city.type'

    name = fields.Char('Name', required=True)
    active = fields.Boolean('active', default=True)


class CountryCity(models.Model):
    _inherit = "res.city"

    hotel_ids = fields.One2many('tt.hotel', 'city_id', 'Hotel')
    banner_ids = fields.One2many('tt.image.banner', 'city_id', 'Banner')
    type_id = fields.Many2one('res.city.type', 'Type')

    @api.one
    def get_hotel_by_city_id_backend(self, city_id, ci_date, co_date, guest, room):
        city_obj = self.browse(city_id)
        room_rate_list = []
        try:
            for hotel_id in city_obj.hotel_ids:
                room_rate_list.append(hotel_id.get_room_by_hotel_id(hotel_id.id, ci_date, co_date, guest, room))
            return room_rate_list
        except:
            return room_rate_list

    def get_hotel_by_city_id(self, city_id, start_date, end_date, user_qty, room_qty):
        return self.env['test.search'].search_hotel_1_1(city_id, start_date, end_date, user_qty, room_qty)

    def get_city_autocomplete(self, dest_name):
        a = []
        city_objs = self.env['res.city'].sudo().search([('name', 'ilike', dest_name)])
        for city_obj in city_objs:
            json_city = {
                'country_id': city_obj.country_id.id,
                'country_name': city_obj.country_id.name,
                'city_id': city_obj.id,
                'city_name': city_obj.name
            }
            a.append(json_city)
        # return list of dict city_id, city_name
        return a

    def get_all_cities(self):
        cities = self.env['res.city'].sudo().search([])
        data = []
        for city in cities:
            json = {
                'id': city.id,
                'type': 'city',
                'name': city.name,
                'display_name': ', '.join([city.name, city.state_id and city.state_id.name or ' ', city.country_id and city.country_id.name or ' ']),
                'country_id': city.country_id.id,
                'country_name': city.country_id.name,
                'state_name': city.state_id and city.state_id.name or 'None',
                'provider': {},
            }
            for provider in city.provider_city_ids:
                json['provider'].update({
                    str(provider.provider_id.provider_code and provider.provider_id.provider_code or provider.provider_id.name).lower(): provider.code,
                })
            data.append(json)
        return data

