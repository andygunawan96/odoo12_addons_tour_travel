from odoo import api, fields, models, _
import json
import traceback, logging
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

    def v2_collect_by_system_tbo_country(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }
        search_req = {
            'provider': 'tbo',
            'type': 'country',
            'limit': '',
            'offset': '',
            'codes': ['All'], #Isi apa pun
        }
        need_to_add_list = []
        url = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        for gw_recs in url['response'][1]:
            for gw_rec in gw_recs:
                need_to_add_list.append([gw_rec['Code'], gw_rec['Name']])

        with open(base_cache_directory + 'tbo/00_master/country.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    def v2_collect_by_system_tbo_city(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }

        need_to_add_list = []
        need_to_add_list.append(['No', 'CityName', 'CityFullName', 'City Code', 'Country Code', 'Hotel qty'])
        no = 1
        # TODO: Read Country CSV Here
        with open(base_cache_directory + 'tbo/00_master/country.csv', 'r') as f:
            country_ids = csv.reader(f)
            # url_resp = [('ID','Indonesia'), ('MY','Malaysia')]
            for gw_rec in country_ids:
                _logger.info("Get City for Country: " + gw_rec[1])
                search_req = {
                    'provider': 'tbo',
                    'type': 'city',
                    'limit': '',
                    'offset': '',
                    'codes': [gw_rec[0],],
                }
                try:
                    city_resp = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                    for city_resp_ea in city_resp['response'][1][0]:
                        need_to_add_list.append([str(no), city_resp_ea['Name'], city_resp_ea['Name'] + '; ' + gw_rec[1], city_resp_ea['Code'], gw_rec[0], -1])
                        no += 1
                except:
                    continue

            with open(base_cache_directory + 'tbo/00_master/city_data.csv', 'w') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerows(need_to_add_list)
            csvFile.close()

    def v2_collect_by_system_tbo_hotellist(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }

        search_req = {
            'provider': 'tbo',
            'type': 'hotel_code',
            'limit': '',
            'offset': '',
            'codes': ['All Hotel',],
        }
        try:
            city_resp = API_CN_HOTEL.get_record_by_api(search_req, api_context)
            filename = base_cache_directory + 'tbo/00_master/all_hotel.txt'
            file = open(filename, 'w')
            file.write(json.dumps(city_resp['response'][1][0]))
            file.close()
        except:
            pass

    # 1a. Collect by System (Schedular)
    # Compiller: Master
    def v2_collect_by_system_tbo(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }

        # self.v2_collect_by_system_tbo_country()
        # self.v2_collect_by_system_tbo_city()
        # self.v2_collect_by_system_tbo_hotellist()

        last_number = 0
        try:
            with open(base_cache_directory + "tbo/00_master/last_const.txt", 'r') as f2:
                cache_file = f2.read()
                last_number = json.loads(cache_file)
                last_number = int(last_number)
        except:
            pass

        per_loop = 50
        with open(base_cache_directory + "tbo/00_master/all_hotel.txt", 'r') as f2:
            cache_file = f2.read()
            all_hotel = json.loads(cache_file)

        hotel_codes = []
        for const in range(int(len(all_hotel) / per_loop)):
            if const < last_number:
                continue

            hotel_codes.append(all_hotel[const * per_loop:(const + 1) * per_loop])
            if len(hotel_codes) < 10:
                continue

            _logger.info("===== Render Const Number: " + str(const) + "/" + str(int(len(all_hotel) / per_loop)) + " =====")

            total_hotel_addded = 0
            rendered_country = {}
            search_req = {
                'provider': 'tbo',
                'type': 'hotel',
                'limit': '',
                'offset': '',
                'codes': hotel_codes,
            }
            hotel_objs = API_CN_HOTEL.get_record_by_api(search_req, api_context)
            # Field Country bisa eg / Egypt
            for hotel_objs in hotel_objs['response'][1]:
                for hotel_obj in hotel_objs:
                    try:
                        if len(hotel_obj['location']['country']) == 2:
                            country_code = hotel_obj['location']['country'].upper()
                        else:
                            country_code = self.env['res.country'].find_country_by_name(hotel_obj['location']['country'])
                            country_code = country_code.code or 'ZZ'

                        if not rendered_country.get(country_code):
                            rendered_country[country_code] = {}
                        city_name = hotel_obj['location']['city']
                        if not rendered_country[country_code].get(city_name):
                            rendered_country[country_code][city_name] = []

                        rendered_country[country_code][city_name].append(hotel_obj)
                    except Exception as e:
                        _logger.error(traceback.format_exc())

            for render_country_code in rendered_country:
                render_country = rendered_country[render_country_code]

                filename = base_cache_directory + "tbo/00_master/" + render_country_code
                if not os.path.isdir(filename):
                    os.makedirs(filename)
                for render_city_code in render_country:
                    render_city = render_country[render_city_code]
                    render_city_code = render_city_code.replace('/',' - ')
                    new_filename = filename + '/' + render_city_code + '.json'

                    try:
                        with open(new_filename, 'r') as f2:
                            record = f2.read()
                            record = json.loads(record)
                            log_str = "Write "+ render_city_code +", " + render_country_code + ": From " + str(len(record)) + " to "
                    except:
                        record = []
                        log_str = "Write New" + render_city_code + ", " + render_country_code + " With "

                    total_hotel_addded += len(render_city)
                    file = open(new_filename, 'w')
                    record += render_city
                    file.write(json.dumps(record))
                    file.close()
                    _logger.info(msg=log_str + str(len(record)) + " Record(s)")

            filename = base_cache_directory + "tbo/00_master/last_const.txt"
            file = open(filename, 'w')
            file.write(json.dumps(const + 1))
            file.close()

            _logger.info(msg="Adding: " + str(total_hotel_addded) + " New Record(s)")
            hotel_codes = []

        _logger.info("===== Done =====")

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Part ini untuk cari per kota penting soale lama klo mesti tunggu 1juta hotel wkwk
    def v2_collect_by_human_tbo(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }
        country_ids = ['id','sg']

        for country in country_ids:
            with open(base_cache_directory + "tbo/00_master/00_city_by_country/"+ country +".txt", 'r') as f2:
                cache_file = f2.read()
                all_city = json.loads(cache_file)

            filename = base_cache_directory + "tbo/00_master_by_city/" + country
            if not os.path.isdir(filename):
                os.makedirs(filename)
            # Loop City dri text diatas
            for city in all_city:
                search_req = {
                    'provider': 'tbo',
                    'type': 'hotel_list_by_city',
                    'limit': '',
                    'offset': '',
                    'codes': [city['Code'],],
                }
                hotel_ids = API_CN_HOTEL.get_record_by_api(search_req, api_context)

                search_req = {
                    'provider': 'tbo',
                    'type': 'hotel',
                    'limit': '',
                    'offset': '',
                    'codes': hotel_ids,
                }
                hotel_objs = API_CN_HOTEL.get_record_by_api(search_req, api_context)

                city['Name'] = city['Name'].replace('/', ' - ')
                new_filename = filename + '/' + city['Name']
                if not os.path.isdir(new_filename):
                    os.makedirs(new_filename)

                file = open(new_filename, 'w')
                file.write(json.dumps(hotel_objs))
                file.close()

        _logger.info("===== Done =====")

    # 1c. Get Country Code
    def v2_get_country_code_tbo(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        _logger.info("===== Done =====")

    # 1d. Get City Code save in tt.hotel.destination
    def v2_get_city_code_tbo(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        _logger.info("===== Done =====")

    # 1e. Get Meal Code
    def v2_get_meal_code_tbo(self):
        return True

    # 1f. Get room Code
    def v2_get_room_code_tbo(self):
        return True

    # 1g. Get Facility Code
    def v2_get_facility_code_tbo(self):
        return True
