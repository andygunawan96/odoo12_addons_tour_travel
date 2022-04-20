from odoo import api, fields, models, _
import json
import logging
import xlrd
from .ApiConnector_Hotel import ApiConnectorHotels
import csv, glob, os
from lxml import html
from ...tools import xmltodict
import csv

_logger = logging.getLogger(__name__)
API_CN_HOTEL = ApiConnectorHotels()


class HotelInformation(models.Model):
    _inherit = 'tt.hotel'

    ###########################################################
    # ====================== New Format ====================  #
    ###########################################################
    # Versi 2: Langsung create record di odoo, tmbahkan ada city jika tidak ketemu

    # 1a. Collect by System (Schedular)
    # Compiller: Master
    # Notes: Ambil data dari vendor (Country, Meal type, Facility, City + destination, Hotel, Other Info)
    # Notes: Simpan ke table masing2x masukan sisane ke other
    # Notes: cara
    # Todo: Perlu catat source data ne
    # Todo: Prepare Cron tiap provider
    def v2_collect_by_system_mgjarvis(self):
        _logger.info("===== Done =====")
        return True

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    def v2_collect_by_human_mgjarvis(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')

        # Unremark buat baca dari cache
        # with open(base_cache_directory + 'mgjarvis/00_master/AvailHotelSummary_V0.csv', 'r') as f:
        #     hotel_ids = csv.reader(f, delimiter="|")
        api_context = {
            'co_uid': self.env.user.id
        }
        search_req = {
            'provider': 'mgjarvis',
            'type': 'GetStaticInformation',
            'limit': '',
            'offset': '',
            'codes': '',
        }
        hotel_ids = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        hotel_fmt_list = {}
        index = False
        for hotel in hotel_ids['response']['response'].split('\r\n')[:-1]:
            hotel = hotel.split('|')
            if not index:
                index = hotel
                continue
            # _logger.info("Processing (" + hotel[1] + ").")
            hotel_fmt = {
                'id': hotel[0],
                'name': hotel[1],
                'street': hotel[3],
                'street2': hotel[19] or '',
                'street3': 'State: ' + hotel[8] or '' + ', Country: ' + hotel[9],
                'description': hotel[16] and 'AirportCode: ' + hotel[16] or '',
                'email': '',
                'images': [],
                'facilities': [],
                'phone': hotel[15],
                'fax': '',
                'zip': hotel[11],
                'website': '',
                'lat': hotel[13],
                'long': hotel[12],
                'rating': hotel[14] and hotel[14].split(',')[0] or 0,
                'hotel_type': '',
                'city': hotel[5],
                'country': hotel[9],
            }
            if not hotel_fmt_list.get(hotel_fmt['country']):
                hotel_fmt_list[hotel_fmt['country']] = {}
            if not hotel_fmt_list[hotel_fmt['country']].get(hotel_fmt['city']):
                hotel_fmt_list[hotel_fmt['country']][hotel_fmt['city']] = []
            hotel_fmt_list[hotel_fmt['country']][hotel_fmt['city']].append(hotel_fmt)

        for country in hotel_fmt_list.keys():
            txt_country = country.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')', '')
            filename = base_cache_directory + "mgjarvis/" + txt_country
            if not os.path.exists(filename):
                os.mkdir(filename)
            for city in hotel_fmt_list[country].keys():
                txt_city = city.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')', '')
                _logger.info("Write File " + txt_country + " City: " + txt_city)
                filename1 = filename + "/" + txt_city + ".json"
                file = open(filename1, 'w')
                file.write(json.dumps(hotel_fmt_list[country][city]))
                file.close()

    # 1c. Get Country Code
    def v2_get_country_code_mgjarvis(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_mgjarvis').id
        with open(base_cache_directory + 'mgjarvis/00_master/Country.csv', 'r') as f:
            country_ids = csv.reader(f)
            for rec in country_ids:
                _logger.info("=== Processing (" + rec[1] + ") ===")

                country_obj = self.env['res.country'].find_country_by_name(rec[1], 1) #by Name
                if not country_obj:
                    country_obj = self.env['res.country'].search([('code', '=', rec[0])], limit=1) #By Code
                country_obj = country_obj and country_obj[0] or self.env['res.country'].create({'name': rec[1]})
                code = rec[0]

                # Create external ID:
                if not self.env['tt.provider.code'].search([('res_model', '=', 'res.country'), ('res_id', '=', country_obj.id),
                                                            ('code', '=', code), ('provider_id', '=', provider_id)]):
                    self.env['tt.provider.code'].create({
                        'res_model': 'res.country',
                        'res_id': country_obj.id,
                        'name': rec[1],
                        'code': code,
                        'provider_id': provider_id,
                    })
        return True

    # 1d. Get City Code
    def v2_get_city_code_mgjarvis(self):
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_mgjarvis(self):
        model = 'tt.meal.type'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_mgjarvis').id
        with open(base_cache_directory + 'mgjarvis/00_master/MealType.csv', 'r') as f:
            meal_type_ids = csv.reader(f)
            for rec in meal_type_ids:
                code = rec[0]
                name = rec[1]
                meal_obj = self.env[model].search([('name','=ilike', name)], limit=1)
                if meal_obj:
                    meal_obj = meal_obj[0]
                else:
                    meal_obj = self.env[model].create({'name': name,})

                # Create external ID:
                if not self.env['tt.provider.code'].search([('res_model', '=', model), ('res_id', '=', meal_obj.id),
                                                            ('code', '=', code), ('provider_id', '=', provider_id)]):
                    self.env['tt.provider.code'].create({
                        'res_model': model,
                        'res_id': meal_obj.id,
                        'name': name,
                        'code': code,
                        'provider_id': provider_id,
                    })
        return []

    # 1f. Get Room Type Code
    def v2_get_room_code_mgjarvis(self):
        model = 'tt.room.type'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_mgjarvis').id
        with open(base_cache_directory + 'mgjarvis/00_master/BedType.csv', 'r') as f:
            bed_type_ids = csv.reader(f)
            for rec in bed_type_ids:
                code = rec[0]
                name = rec[1]
                meal_obj = self.env[model].search([('name', '=ilike', name)], limit=1)
                if meal_obj:
                    meal_obj = meal_obj[0]
                else:
                    meal_obj = self.env[model].create({'name': name, })

                # Create external ID:
                if not self.env['tt.provider.code'].search([('res_model', '=', model), ('res_id', '=', meal_obj.id),
                                                            ('code', '=', code), ('provider_id', '=', provider_id)]):
                    self.env['tt.provider.code'].create({
                        'res_model': model,
                        'res_id': meal_obj.id,
                        'name': name,
                        'code': code,
                        'provider_id': provider_id,
                    })
        return []

    # 1g. Get Facility Code
    def v2_get_facility_code_mgjarvis(self):
        return True
