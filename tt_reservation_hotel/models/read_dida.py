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
    def v2_collect_by_system_dida(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }
        for rec in ['Country', 'BedType', 'BreakfastType', 'PropertyCategory', 'MealType']:
            search_req = {
                'provider': 'dida',
                'type': 'Get' + rec + 'List',
                'limit': '',
                'offset': '',
                'codes': '',
            }
            need_to_add_list = []
            try:
                a = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                a = a['response'][1]
                if rec == 'Country':
                    for gw_rec in a['Countries']:
                        need_to_add_list.append([gw_rec['ISOCountryCode'], gw_rec['CountryName'].encode("utf-8")])
                elif rec == 'BreakfastType':
                    for gw_rec in a['Breakfasts']:
                        need_to_add_list.append([gw_rec['ID'], gw_rec['Name']])
                else:
                    # BedTypes, Breakfasts, PropertyCategorys, MealTypes
                    for gw_rec in a[rec + 's']:
                        need_to_add_list.append([gw_rec['ID'], gw_rec.get('Name') or gw_rec.get('Description_EN')])

                with open(base_cache_directory + 'dida/00_master/' + rec + '.csv', 'w') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerows(need_to_add_list)
                csvFile.close()
            except:
                _logger.info('Error While rendering Get' + rec + 'List')
                continue

        # Get City by country Start
        with open(base_cache_directory + 'dida/00_master/Country.csv', 'r') as f:
            country_ids = csv.reader(f)
            need_to_add_list = []
            for rec in country_ids:
                _logger.info("=== Processing (" + rec[1] + ") ===")
                search_req = {
                    'provider': 'dida',
                    'type': 'GetCityList',
                    'limit': '',
                    'offset': '',
                    'codes': rec[0],
                }
                a = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                try:
                    for gw_rec in a['response'][1]['Cities']:
                        _logger.info("City: " + gw_rec['CityName'] + ".")
                        need_to_add_list.append([gw_rec['CityCode'], gw_rec['CityName'].encode("utf-8"),
                                                 gw_rec['CityLongName'].encode("utf-8"),
                                                 gw_rec['CountryCode']])
                except:
                    _logger.info("No City for: " + rec[1] + ".")
                    continue
        f.close()
        with open(base_cache_directory + 'dida/00_master/City.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()
        # Get City by country End
        _logger.info("===== Done =====")
        return True

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    def v2_collect_by_human_dida(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        with open(base_cache_directory + 'dida/00_master/AvailHotelSummary_V0.csv', 'r') as f:
            hotel_ids = csv.reader(f, delimiter="|")

            hotel_fmt_list = {}
            index = False
            for hotel in hotel_ids:
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
                filename = base_cache_directory + "dida/" + txt_country
                if not os.path.exists(filename):
                    os.mkdir(filename)
                for city in hotel_fmt_list[country].keys():
                    txt_city = city.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')', '')
                    _logger.info("Write File " + txt_country + " City: " + txt_city)
                    filename1 = filename + "/" + txt_city + ".json"
                    file = open(filename1, 'w')
                    file.write(json.dumps(hotel_fmt_list[country][city]))
                    file.close()
        f.close()

    def v2_collect_by_human_csv_dida(self):
        return True

    # 1c. Get Country Code
    def v2_get_country_code_dida(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_dida').id
        with open(base_cache_directory + 'dida/00_master/Country.csv', 'r') as f:
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

    # 1d. Get City Code Old Ver cari City
    def v2_get_city_code_dida_old(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_dida').id
        with open(base_cache_directory + 'dida/00_master/City.csv', 'r') as f:
            city_ids = csv.reader(f)
            for rec in city_ids:
                code = rec[0] #6051357
                name = rec[1].split("'")[1] #b'Ransol'
                code_name = rec[2].split("'")[1] #b'Ransol, Andorra'
                country_code = rec[3] #AD

                _logger.info('Render ' + name + ' Start')
                city_obj = self.env['res.city'].find_city_by_name(name, 1)
                if city_obj:
                    city_obj = city_obj[0]
                    _logger.info('Find Old Record')
                else:
                    code_id = self.env['tt.provider.code'].search([('code','=', country_code), ('provider_id','=', provider_id)])
                    country_id = code_id and code_id[0].res_id or False
                    city_obj = self.env['res.city'].create({
                        'name': name,
                        'country_id': country_id,
                    })
                    _logger.info('Create New Record')

                # Create external ID:
                if not self.env['tt.provider.code'].search([('res_model','=','res.city'), ('res_id','=',city_obj.id),
                                                            ('code','=', code), ('provider_id','=',provider_id)]):
                    self.env['tt.provider.code'].create({
                        'res_model': 'res.city',
                        'res_id': city_obj.id,
                        'name': code_name,
                        'code': code,
                        'provider_id': provider_id,
                    })
                    _logger.info('Create New Code')
                else:
                    _logger.info('Code already Exist Code')
            _logger.info('Render Done')
        return True

    # 1d. Get City Code
    # Fungsi yg Jalan cman tdak digunakan
    def v2_get_city_code_dida_1(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_dida').id
        with open(base_cache_directory + 'dida/00_master/City.csv', 'r') as f:
            city_ids = csv.reader(f)
            idx = 0
            for rec in city_ids:
                if idx < -1:
                    idx += 1
                    continue
                code = rec[0] #6051357
                name = rec[1].split("'")[1] #b'Ransol'
                code_name = rec[2].split("'")[1] #b'Ransol, Andorra'
                country_code = rec[3] #AD
                country_name = self.env['res.country'].search([('code','=',country_code)], limit=1).name

                _logger.info('Render ' + name + ' Start')
                old_obj = self.env['tt.provider.code'].search([('res_model', '=', 'tt.hotel.destination'), ('code', '=', code), ('provider_id', '=', provider_id)])
                if not old_obj:
                    new_dict = {
                        'id': False,
                        'name': name,
                        'city_str': name,
                        'state_str': '',
                        'country_str': country_name,
                    }
                    is_exact, new_obj = self.env['tt.hotel.destination'].find_similar_obj(new_dict)
                    if not is_exact:
                        new_obj = self.env['tt.hotel.destination'].create(new_dict)
                        new_obj.fill_obj_by_str()
                        _logger.info('Create New Destination {} with code {}'.format(name, code))
                    else:
                        _logger.info('Destination already Exist Code for {}, Country {}'.format(name, country_name))

                    self.env['tt.provider.code'].create({
                        'res_model': 'tt.hotel.destination',
                        'res_id': new_obj.id,
                        'name': code_name,
                        'code': code,
                        'provider_id': provider_id,
                    })
                    _logger.info('Create External ID {} with id {}'.format(code, str(new_obj.id)))
                else:
                    _logger.info('External ID {} already Exist in {} with id {}'.format(code, old_obj.res_model, str(old_obj.res_id)))
                idx += 1
                if idx % 100 == 0:
                    _logger.info('Saving Record until ' + str(idx))
                    self.env.cr.commit()
            _logger.info('Render Done')
        return True

    # 1d. Get City Code
    # Gunakan ini Soale dida tidak bisa search by city code
    # DI versi 15 juli 2021 logic GW
    # cek ada external code nya tidak jika ada yg di kirim ke vendor city code nya
    # Jika tidak ada ambil hotel code untuk dest tersebut
    def v2_get_city_code_dida(self):
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_dida(self):
        model = 'tt.meal.type'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_dida').id
        with open(base_cache_directory + 'dida/00_master/MealType.csv', 'r') as f:
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
    def v2_get_room_code_dida(self):
        model = 'tt.room.type'
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_dida').id
        with open(base_cache_directory + 'dida/00_master/BedType.csv', 'r') as f:
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
    def v2_get_facility_code_dida(self):
        return True
