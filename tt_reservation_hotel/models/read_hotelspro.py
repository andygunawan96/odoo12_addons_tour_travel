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
    def v2_collect_by_system_hotelspro(self):
        return True

    def provider_code_to_dict(self, provider_code_objs):
        result = {}
        for rec in provider_code_objs:
            if rec.res_model == 'tt.hotel.destination':
                obj = self.env['tt.hotel.destination'].browse(rec.res_id)
                result[rec.code] = [rec.name, obj.country_id.name]
            else:
                result[rec.code] = rec.name
        return result

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    def v2_collect_by_human_hotelspro(self):
        model = 'tt.hotel'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_hotelspro').id

        cache_city = self.provider_code_to_dict(self.env['tt.provider.code'].search([('res_model','=','tt.hotel.destination'),('provider_id','=',provider_id)]))
        cache_fac = self.provider_code_to_dict(self.env['tt.provider.code'].search([('res_model','=','tt.hotel.facility'),('provider_id','=',provider_id)]))
        # cache_type = self.env['tt.provider.code'].search([('res_model','=',''),('res_model','=','res.city')])

        cache_hotel = {}
        type = {}
        filenames = ['hotels-', ]  # ['hoteltypes-', 'facilities-', 'country-', 'mealtypes-','destinations-']
        for filename in filenames:
            number = 1
            err_counter = 0
            while number:
                try:
                    _logger.info("Opening file (" + base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + ").")
                    with open(base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + '.json') as f:
                        data = json.load(f)
                        for obj in data:
                            if cache_city.get(obj.get('destination')):
                                city_name = cache_city[obj['destination']][0].replace('/', '-').replace("\'", '-') or ''
                                country_name = cache_city[obj['destination']][1] or ''
                            else:
                                # _logger.info("Skipping: Destination" + obj.get('destination'))
                                city_name = obj.get('destination')
                                country_name = 'other:'

                            if not cache_hotel.get(country_name):
                                cache_hotel[country_name] = {}
                            if not cache_hotel[country_name].get(city_name):
                                cache_hotel[country_name][city_name] = []
                            # _logger.info("Process: " + json.dumps(obj))
                            cache_hotel[country_name][city_name].append({
                                'id': obj.get('code'),
                                'name': obj['name'],
                                'street': obj.get('address') and obj['address'] or '',
                                'street2': '',
                                'street3': '',
                                'description': obj.get('descriptions') and obj['descriptions'].get('hotel_information'),
                                'email': obj.get('email') or '',
                                'images': obj['images'] and [rec['original'] for rec in obj['images']] or [],
                                'facilities': obj['facilities'] and [cache_fac[rec] for rec in obj['facilities']] or [],
                                'phone': obj.get('phone') and obj['phone'] or '',
                                'fax': '',
                                'zip': obj.get('zipcode'),
                                'website': '',
                                'lat': obj.get('latitude'),
                                'long': obj.get('longitude'),
                                'rating': obj.get('stars') and int(obj['stars']) or 0,
                                'hotel_type': obj.get('hotel_type') or '',
                                'city': city_name,
                                'country': country_name,
                            })
                        if number % 3 == 0:
                            _logger.info("Write to file number:" + str(number))
                            for country in cache_hotel.keys():
                                for rec in cache_hotel[country].keys():
                                    if not os.path.exists(base_cache_directory + "hotelspro_file/result/" + country):
                                        os.mkdir(base_cache_directory + "hotelspro_file/result/" + country)
                                    temp_filename = base_cache_directory + "hotelspro_file/result/" + country + "/" + rec + ".json"
                                    try:
                                        with open(temp_filename, 'r') as f2:
                                            a = f2.read()
                                            old_record = json.loads(a)
                                            old_record += cache_hotel[country][rec]
                                        f2.close()
                                    except:
                                        old_record = cache_hotel[country][rec]

                                    file = open(temp_filename, 'w')
                                    file.write(json.dumps(old_record))
                                    file.close()
                            cache_hotel = {}
                    err_counter = 0
                except IOError as e:
                    _logger.error("Couldn't open or write to file (%s)." % e)
                    # cache_hotel[filename[:-1]] = type
                    err_counter += 1
                    if err_counter == 5:
                        break
                number += 1

        _logger.info("===== Hotelspro Hotel Done =====")
        return True

    def v2_collect_by_human_csv_hotelspro(self):
        return True

    # 1c. Get Country Code
    def v2_get_country_code_hotelspro(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_hotelspro').id
        cache_hotel = {}
        type = {}
        filenames = ['countries-',] #['hoteltypes-', 'facilities-', 'countries-']
        for filename in filenames:
            number = 1
            while number:
                try:
                    _logger.info("Opening file (" + base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + ").")
                    with open(base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + '.json') as f:
                        data = json.load(f)
                        for rec in data:
                            type[rec['code']] = rec['name']
                    number += 1
                except IOError as e:
                    _logger.error("Couldn't open or write to file (%s)." % e)
                    cache_hotel[filename[:-1]] = type
                    break

        for filename in filenames:
            for key, val in cache_hotel[filename[:-1]].items():
                _logger.info("=== Processing (" + val + ") ===")

                country_obj = self.env['res.country'].search([('code', '=ilike', key)], limit=1)  # By Code
                if not country_obj:
                    country_obj = self.env['res.country'].find_country_by_name(val, 1)  # by Name
                country_obj = country_obj and country_obj[0] or self.env['res.country'].create({'name': val})

                # Create external ID:
                if not self.env['tt.provider.code'].search([('res_model', '=', 'res.country'), ('res_id', '=', country_obj.id), ('code', '=', key), ('provider_id', '=', provider_id)]):
                    self.env['tt.provider.code'].create({
                        'res_model': 'res.country',
                        'res_id': country_obj.id,
                        'name': val,
                        'code': key,
                        'provider_id': provider_id,
                    })
        return True

    # 1d. Get City Code
    def v2_get_city_code_hotelspro(self):
        model = 'res.city'
        model1 = 'tt.hotel.destination'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_hotelspro').id
        cache_hotel = {}
        type = {}
        filenames = ['destinations-', ]  # ['hoteltypes-', 'facilities-', 'country-', 'mealtypes-','destinations-']
        for filename in filenames:
            number = 1
            err_counter = 0
            while number:
                try:
                    _logger.info("Opening file (" + base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + ").")
                    with open(base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + '.json') as f:
                        data = json.load(f)
                        for rec in data:
                            # type[rec['code']] = [rec['name'],rec['country'].upper()]
                            if not type.get(rec['country'].upper()):
                                type[rec['country'].upper()] = {}
                            type[rec['country'].upper()][rec['code']] = (rec['name'])
                    err_counter = 0
                except IOError as e:
                    _logger.error("Couldn't open or write to file (%s)." % e)
                    cache_hotel[filename[:-1]] = type
                    err_counter += 1
                    if err_counter == 5:
                        break
                number += 1

        for filename in filenames:
            for country in cache_hotel[filename[:-1]]:
                country_obj = self.env['res.country'].search([('code', '=', country)], limit=1)
                if not country_obj:
                    continue
                _logger.info("===== Processing " + country_obj.name + " =====")
                for key, val in cache_hotel[filename[:-1]][country].items():
                    _logger.info("=== Processing (" + val + ", " + country_obj.name + ") ===")

                    if self.env['tt.provider.code'].search([('res_model', '=', model1), ('code', '=', key), ('provider_id', '=', provider_id)]):
                        continue
                    city_obj = self.env[model].search([('name', '=ilike', val), ('country_id', '=', country_obj.id)], limit=1)  # By Code
                    res_obj = self.env[model1].create({
                        'name': val,
                        'city_str': val,
                        'city_id': city_obj and city_obj.id or False,
                        'country_str': country_obj.name,
                        'country_id': country_obj.id,
                    })
                    for rec in [model, model1]:
                        # Create external ID:
                        if not self.env['tt.provider.code'].search([('res_model', '=', rec), ('res_id', '=', res_obj.id), ('code', '=', key),('provider_id', '=', provider_id)]):
                            self.env['tt.provider.code'].create({
                                'res_model': rec,
                                'res_id': res_obj.id,
                                'name': val,
                                'code': key,
                                'provider_id': provider_id,
                            })
                self.env.cr.commit()
        _logger.info("===== Hotelspro City Done =====")
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_hotelspro(self):
        model = 'tt.meal.type'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_hotelspro').id
        cache_hotel = {}
        type = {}
        filenames = ['mealtypes-', ]  # ['hoteltypes-', 'facilities-', 'country-', 'mealtypes-']
        for filename in filenames:
            number = 1
            while number:
                try:
                    _logger.info("Opening file (" + base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + ").")
                    with open(base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + '.json') as f:
                        data = json.load(f)
                        for rec in data:
                            type[rec['code']] = rec['name']
                    number += 1
                except IOError as e:
                    _logger.error("Couldn't open or write to file (%s)." % e)
                    cache_hotel[filename[:-1]] = type
                    break

        for filename in filenames:
            for key, val in cache_hotel[filename[:-1]].items():
                _logger.info("=== Processing (" + val + ") ===")

                res_obj = self.env[model].search([('name', '=ilike', val)], limit=1)  # By Code
                res_obj = res_obj and res_obj[0] or self.env[model].create({'name': val})

                # Create external ID:
                if not self.env['tt.provider.code'].search(
                        [('res_model', '=', model), ('res_id', '=', res_obj.id), ('code', '=', key),
                         ('provider_id', '=', provider_id)]):
                    self.env['tt.provider.code'].create({
                        'res_model': model,
                        'res_id': res_obj.id,
                        'name': val,
                        'code': key,
                        'provider_id': provider_id,
                    })
        return True

    # 1f. Get Room Type Code
    def v2_get_room_code_hotelspro(self):
        model = 'tt.room.type'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_hotelspro').id
        cache_hotel = {}
        type = {}
        filenames = ['roomtypes-', ]  # ['hoteltypes-', 'facilities-', 'country-', 'mealtypes-', 'roomcategories-', 'roomtypes-']
        for filename in filenames:
            number = 1
            while number:
                try:
                    _logger.info("Opening file (" + base_cache_directory + 'hotelspro_file/data/' + filename + str(
                        number - 1) + ").")
                    with open(
                            base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + '.json') as f:
                        data = json.load(f)
                        for rec in data:
                            type[rec['code']] = rec['name']
                    number += 1
                except IOError as e:
                    _logger.error("Couldn't open or write to file (%s)." % e)
                    cache_hotel[filename[:-1]] = type
                    break

        for filename in filenames:
            for key, val in cache_hotel[filename[:-1]].items():
                _logger.info("=== Processing (" + val + ") ===")

                res_obj = self.env[model].search([('name', '=ilike', val)], limit=1)  # By Code
                res_obj = res_obj and res_obj[0] or self.env[model].create({'name': val})

                # Create external ID:
                if not self.env['tt.provider.code'].search(
                        [('res_model', '=', model), ('res_id', '=', res_obj.id), ('code', '=', key),
                         ('provider_id', '=', provider_id)]):
                    self.env['tt.provider.code'].create({
                        'res_model': model,
                        'res_id': res_obj.id,
                        'name': val,
                        'code': key,
                        'provider_id': provider_id,
                    })
        return True

    # 1g. Get Facility Code
    def v2_get_facility_code_hotelspro(self):
        model = 'tt.hotel.facility'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_hotelspro').id
        cache_hotel = {}
        type = {}
        filenames = ['facilities-', ]  # ['hoteltypes-', 'facilities-', 'country-', 'mealtypes-']
        for filename in filenames:
            number = 1
            while number:
                try:
                    _logger.info("Opening file (" + base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + ").")
                    with open(base_cache_directory + 'hotelspro_file/data/' + filename + str(number - 1) + '.json') as f:
                        data = json.load(f)
                        for rec in data:
                            type[rec['code']] = rec['name']
                    number += 1
                except IOError as e:
                    _logger.error("Couldn't open or write to file (%s)." % e)
                    cache_hotel[filename[:-1]] = type
                    break

        for filename in filenames:
            for key, val in cache_hotel[filename[:-1]].items():
                _logger.info("=== Processing (" + val + ") ===")

                res_obj = self.env[model].search([('name', '=ilike', val)], limit=1)  # By Code
                res_obj = res_obj and res_obj[0] or self.env[model].create({'name': val, 'facility_type_id': self.env['tt.hotel.facility.type'].search([],limit=1)[0].id })

                # Create external ID:
                if not self.env['tt.provider.code'].search(
                        [('res_model', '=', model), ('res_id', '=', res_obj.id), ('code', '=', key),
                         ('provider_id', '=', provider_id)]):
                    self.env['tt.provider.code'].create({
                        'res_model': model,
                        'res_id': res_obj.id,
                        'name': val,
                        'code': key,
                        'provider_id': provider_id,
                    })
        return True
