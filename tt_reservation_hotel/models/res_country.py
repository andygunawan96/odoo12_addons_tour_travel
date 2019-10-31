from odoo import models, fields, api
from datetime import date, datetime, timedelta


class CityType(models.Model):
    _name = 'res.city.type'
    _description = 'Explaining City type. Example: CITY, KABUPATEN, DISTRICT etc.'

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
