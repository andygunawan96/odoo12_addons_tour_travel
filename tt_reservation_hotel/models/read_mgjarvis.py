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
        get_data = ['GetNationalities', 'GetMealPlans', 'GetPromotionTypes', 'GetDestinations', 'GetHotelList']
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')

        # codes = [{'name':'Jakarta','code':'ID-CGK'}, {'name':'Surabaya','code':'ID-SUB'}]
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_mg').id
        codes = [{
            'name': x.name.split(',')[0].upper(),
            'code': x.code} for x in self.env['tt.provider.code'].search([('res_model', '=', 'tt.hotel.destination'),('provider_id', '=', provider_id)]) if 'ID-' in x.code]

        for loop_code in codes:
            txt_city = loop_code['name']
            code = loop_code['code']
            result = []
            result_fmt = []

            api_context = {
                'co_uid': self.env.user.id
            }
            search_req = {
                'provider': 'mgjarvis',
                'type': 'GetHotelList',
                'limit': '',
                'offset': '',
                'codes': code,
            }
            hotel_ids = API_CN_HOTEL.get_record_by_api(search_req, api_context)

            # for hotel_id in hotel_ids['response']['result']['hotels']:
            #     search_req = {
            #         'provider': 'mgjarvis',
            #         'type': 'GetHotelDetail',
            #         'limit': '',
            #         'offset': '',
            #         'codes': hotel_id['code'],
            #     }
            #     hotel_obj = API_CN_HOTEL.get_record_by_api(search_req, api_context)
            #     # Save Original from vendor
            #     result.append(hotel_obj['response']['result'])
            #
            #     # Formating STD Result
            #     hotel_obj = hotel_obj['response']['result']
            #     hotel_fmt = {
            #         'id': self.get_xml_data(hotel_obj, ['hotelCode']),
            #         'name': self.get_xml_data(hotel_obj, ['name']),
            #         'street': self.get_xml_data(hotel_obj, ['address','address1']),
            #         'street2': self.get_xml_data(hotel_obj, ['address','address2']),
            #         'street3': self.get_xml_data(hotel_obj, ['address','area']) and 'Area: ' + self.get_xml_data(hotel_obj, ['address','area']) or '',
            #         'description': self.get_xml_data(hotel_obj, ['longDescription','content']),
            #         'email': self.get_xml_data(hotel_obj, ['reservation','email']),
            #         'images': [x['url'] for x in self.get_xml_data(hotel_obj, ['photo','image'])],
            #         'facilities': [], #ada cman stuktur facility ada yg mode pertanyaan contoh: 'Is Internet available for guests: Free'
            #         'phone': self.get_xml_data(hotel_obj, ['reservation','telephone']),
            #         'fax': self.get_xml_data(hotel_obj, ['reservation','fax']),
            #         'zip': self.get_xml_data(hotel_obj, ['address','zipCode']),
            #         'website': self.get_xml_data(hotel_obj, ['website',]),
            #         'lat': self.get_xml_data(hotel_obj, ['geoLocation','latitude']),
            #         'long': self.get_xml_data(hotel_obj, ['geoLocation','longitude']),
            #         'rating': self.get_xml_data(hotel_obj, ['rating',]),
            #         'hotel_type': self.get_xml_data(hotel_obj, ['type',]),
            #         'city': self.get_xml_data(hotel_obj, ['address','cityName']),
            #         'country': self.get_xml_data(hotel_obj, ['address','countryName']),
            #     }
            #     result_fmt.append(hotel_fmt)

            try:
                for hotel_id in hotel_ids['response']['result']['hotels']:
                    hotel_obj = hotel_id
                    hotel_fmt = {
                        'id': self.get_xml_data(hotel_obj, ['address','cityCode']) + '~' + self.get_xml_data(hotel_obj, ['code']),
                        'name': self.get_xml_data(hotel_obj, ['name']),
                        'street': self.get_xml_data(hotel_obj, ['address', 'line1']),
                        'street2': self.get_xml_data(hotel_obj, ['address', 'line2']),
                        'street3': self.get_xml_data(hotel_obj, ['address', 'area']) and 'Area: ' + self.get_xml_data(
                            hotel_obj, ['address', 'area']) or '',
                        'description': self.get_xml_data(hotel_obj, ['longDescription', 'content']),
                        'email': self.get_xml_data(hotel_obj, ['reservation', 'email']),
                        'images': [x['url'] for x in self.get_xml_data(hotel_obj, ['photo', 'image'])],
                        'facilities': [],
                        # ada cman stuktur facility ada yg mode pertanyaan contoh: 'Is Internet available for guests: Free'
                        'phone': self.get_xml_data(hotel_obj, ['reservation', 'telephone']),
                        'fax': self.get_xml_data(hotel_obj, ['reservation', 'fax']),
                        'zip': self.get_xml_data(hotel_obj, ['address', 'zipCode']),
                        'website': self.get_xml_data(hotel_obj, ['website', ]),
                        'lat': self.get_xml_data(hotel_obj, ['geoLocation', 'latitude']),
                        'long': self.get_xml_data(hotel_obj, ['geoLocation', 'longitude']),
                        'rating': self.get_xml_data(hotel_obj, ['rating', ]),
                        'hotel_type': self.get_xml_data(hotel_obj, ['type', ]),
                        'city': self.get_xml_data(hotel_obj, ['address', 'cityName']),
                        'country': self.get_xml_data(hotel_obj, ['address', 'countryName']),
                    }
                    result_fmt.append(hotel_fmt)
                # Write Master
                filename = base_cache_directory + "mgjarvis_master/" + code.split('-')[0]
                if not os.path.exists(filename):
                    os.mkdir(filename)
                _logger.info("Write File " + code.split('-')[0] + " City: " + txt_city)
                filename1 = filename + "/" + txt_city + ".json"
                file = open(filename1, 'w')
                file.write(json.dumps(result))
                file.close()
            except:
                _logger.info("Error City: " + txt_city)

            # Write Result
            filename = base_cache_directory + "mgjarvis/" + code.split('-')[0]
            if not os.path.exists(filename):
                os.mkdir(filename)
            _logger.info("Write File " + code.split('-')[0] + " City: " + txt_city)
            filename1 = filename + "/" + txt_city + ".json"
            file = open(filename1, 'w')
            file.write(json.dumps(result_fmt))
            file.close()
        _logger.info("===== Done =====")
        return True

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    # Data pnya Jarvis
    def v2_collect_by_human_mgjarvis_1(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')

        # Unremark buat baca dari cache
        with open(base_cache_directory + 'mgjarvis/00_master/hotel_from_vendor.csv', 'r') as f:
            hotel_ids = csv.reader(f, delimiter=";")
        hotel_fmt_list = {}
        index = False
        for hotel in hotel_ids.split('\r\n')[:-1]:
            hotel = hotel.split('|')
            if not index:
                index = hotel
                continue
            # _logger.info("Processing (" + hotel[1] + ").")
            hotel_fmt = {
                'id': hotel[4], #ID-SUB~ID00123 (country - city ~ hotel code)
                'name': hotel[5],
                'street': hotel[9],
                'street2': hotel[10] or '',
                'street3': '',
                'description': '',
                'email': hotel[16],
                'images': [],
                'facilities': [],
                'phone': hotel[15],
                'fax': '',
                'zip': hotel[11],
                'website': hotel[14],
                'lat': hotel[8],
                'long': hotel[7],
                'rating': hotel[6] and hotel[6].split(',')[0] or 0,
                'hotel_type': hotel[-1],
                'city': hotel[3],
                'country': hotel[1],
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

    def v2_collect_by_human_mgjarvis(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')

        # Unremark buat baca dari cache
        with open(base_cache_directory + 'mgjarvis/00_master/Priority One.csv', 'r') as f:
            hotel_ids = csv.reader(f, delimiter=";")
            hotel_fmt_list = {}
            index = 0
            for hotel in hotel_ids:
                index += 1
                if index < 2:
                    continue
                # _logger.info("Processing (" + hotel[1] + ").")
                hotel_fmt = {
                    'id': hotel[2] + '~' + hotel[4], #ID-SUB~ID00123 (country - city ~ hotel code)
                    'name': hotel[8],
                    'street': hotel[12],
                    'street2': hotel[13] or '',
                    'street3': '',
                    'description': 'Check In From: ' + hotel[15] + '; ' + 'Check Out To: ' + hotel[16],
                    'email': hotel[18],
                    'images': [],
                    'facilities': [],
                    'phone': hotel[17],
                    'fax': '',
                    'zip': hotel[14],
                    'website': hotel[15],
                    'lat': hotel[11],
                    'long': hotel[10],
                    'rating': hotel[9] and hotel[9].split(',')[0] or 0,
                    'hotel_type': hotel[-1],
                    'city': hotel[3],
                    'country': hotel[1],
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
        filename = base_cache_directory + 'mgjarvis/00_master/Country.csv'
        try:
            api_context = {
                'co_uid': self.env.user.id
            }
            search_req = {
                'provider': 'mgjarvis',
                'type': 'GetNationalities',
                'limit': '',
                'offset': '',
                'codes': '',
            }
            nationality_ids = API_CN_HOTEL.get_record_by_api(search_req, api_context)
            _logger.info("===== Data Done =====")

            # Write Data
            file = open(filename, 'w')
            file.write(json.dumps(nationality_ids))
            file.close()

        except:
            # Error Retrieving new Nationality Data using the old one if Exist
            _logger.info("===== Error Retrieving new Data using the old one if aE =====")

        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_mg').id
        with open(filename, 'r') as f:
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
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        filename = base_cache_directory + 'mgjarvis/00_master/City.json'
        try:
            api_context = {
                'co_uid': self.env.user.id
            }
            search_req = {
                'provider': 'mgjarvis',
                'type': 'GetDestinations',
                'limit': '',
                'offset': '',
                'codes': '',
            }
            # nationality_ids = API_CN_HOTEL.get_record_by_api(search_req, api_context)
            # _logger.info("===== Data Done =====")

            # Write Data
            # file = open(filename, 'w')
            # file.write(json.dumps(nationality_ids))
            # file.close()

        except:
            # Error Retrieving new Nationality Data using the old one if Exist
            _logger.info("===== Error Retrieving new Data using the old one if Exist =====")

        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_mg').id
        with open(filename, 'r') as f:
            txt_data = f.read()
            country_ids = json.loads(txt_data)
            country_ids = country_ids['response']['result']
            for rec in country_ids.keys():
                _logger.info("=== Processing (" + rec + ") ===")

                country_obj = self.env['res.country'].search([('code', '=', rec)], limit=1)  # By Code
                if not country_obj:
                    country_obj = self.env['res.country'].find_country_by_name(country_ids[rec]['name'], 1)  # by Name
                country_obj = country_obj and country_obj[0] or self.env['res.country'].create({'name': country_ids[rec]['name']})
                code = rec[0]

                # Create external ID:
                if not self.env['tt.provider.code'].search([('res_model', '=', 'res.country'), ('res_id', '=', country_obj.id), ('code', '=', rec), ('provider_id', '=', provider_id)]):
                    _logger.info("Create " + country_ids[rec]['name'] + " with code " + rec)
                    self.env['tt.provider.code'].create({
                        'res_model': 'res.country',
                        'res_id': country_obj.id,
                        'name': country_ids[rec]['name'],
                        'code': rec,
                        'provider_id': provider_id,
                    })
                else:
                    _logger.info("Skipping " + country_ids[rec]['name'] + " with code " + rec + " already Exist")

                idx = 0
                for city_dta in country_ids[rec]['city']:
                    name = city_dta['name']
                    code = city_dta['code']
                    old_obj = self.env['tt.provider.code'].search(
                        [('res_model', '=', 'tt.hotel.destination'), ('code', '=', code),
                         ('provider_id', '=', provider_id)], limit=1)
                    if not old_obj:
                        new_dict = {
                            'id': False,
                            'name': name,
                            'city_str': name,
                            'state_str': '',
                            'country_str': country_obj.name,
                        }
                        is_exact, new_obj = self.env['tt.hotel.destination'].find_similar_obj(new_dict, False)
                        if not is_exact:
                            new_obj = self.env['tt.hotel.destination'].create(new_dict)
                            new_obj.fill_obj_by_str()
                            _logger.info('Create New Destination {} with code {}'.format(name, code))
                        else:
                            _logger.info('Destination already Exist for {}, Country {}'.format(name, country_obj.name))

                        self.env['tt.provider.code'].create({
                            'res_model': 'tt.hotel.destination',
                            'res_id': new_obj.id,
                            'name': name + ", " + country_obj.name,
                            'code': code,
                            'provider_id': provider_id,
                        })
                        _logger.info('{}. Create Provider Code for {}'.format(str(idx), name))
                    else:
                        _logger.info('Skipping {} already Exist in {} with id {}'.format(code, old_obj.res_model,
                                                                                            str(old_obj.res_id)))
                    idx += 1
                    if idx % 50 == 0:
                        _logger.info('Saving Record until ' + str(idx))
                        self.env.cr.commit()
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_mgjarvis(self):
        model = 'tt.meal.type'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        filename = base_cache_directory + 'mgjarvis/00_master/MealType.json'
        try:
            api_context = {
                'co_uid': self.env.user.id
            }
            search_req = {
                'provider': 'mgjarvis',
                'type': 'GetMealPlans',
                'limit': '',
                'offset': '',
                'codes': '',
            }
            nationality_ids = API_CN_HOTEL.get_record_by_api(search_req, api_context)
            _logger.info("===== Data Done =====")

            # Write Data
            file = open(filename, 'w')
            file.write(json.dumps(nationality_ids))
            file.close()

        except:
            # Error Retrieving new Nationality Data using the old one if Exist
            _logger.info("===== Error Retrieving new Data using the old one if Exist =====")

        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_mg').id
        with open(filename, 'r') as f:
            txt_data = f.read()
            country_ids = json.loads(txt_data)
            country_ids = country_ids['response']['result']
            for rec in country_ids.keys():
                code = rec
                name = country_ids[rec]['name']
                meal_obj = self.env[model].search([('name', '=ilike', name)], limit=1)
                if meal_obj:
                    meal_obj = meal_obj[0]
                    _logger.info('Create New Meal type {} with code {}'.format(name, code))
                else:
                    meal_obj = self.env[model].create({'name': name, })
                    _logger.info('Meal Type already Exist for {}'.format(name))

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
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_mg').id
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
