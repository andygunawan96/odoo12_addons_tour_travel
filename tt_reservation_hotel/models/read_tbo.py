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
            'codes': '',
        }
        need_to_add_list = []
        url = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        for gw_rec in url['response'][1]:
            need_to_add_list.append([gw_rec['code'], gw_rec['name']])

        with open(base_cache_directory + 'tbo/master/country.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    def v2_collect_by_system_tbo_city(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }

        # TODO: Read Country CSV Here
        url_resp = [('ID','Indonesia'), ('MY','Malaysia')]
        for gw_rec in url_resp:
            _logger.info("Get City for Country: " + gw_rec[1])
            search_req = {
                'provider': 'tbo',
                'type': 'city',
                'limit': '',
                'offset': '',
                'codes': gw_rec[0],
            }
            try:
                city_resp = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                filename = base_cache_directory + 'tbo/master/' + gw_rec[0].lower() + '.txt'
                file = open(filename, 'w')
                file.write(json.dumps(city_resp['response'][1]))
                file.close()
            except:
                continue

    # 1a. Collect by System (Schedular)
    # Compiller: Master
    def v2_collect_by_system_tbo(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }

        self.v2_collect_by_system_tbo_country()
        self.v2_collect_by_system_tbo_city()

        i = 1
        stopper = 0
        rendered_city = []
        need_to_add_list = []
        try:
            with open(base_cache_directory + "tbo/master_csv/result_data.csv", 'r') as file:
                file_content = csv.reader(file)
                for rec in file_content:
                    i += 1
                    rendered_city.append(rec[1].lower())
                    need_to_add_list.append(rec)
                file.close()
        except:
            need_to_add_list.append(['No', 'City', 'City Code', 'Country', 'Hotel qty'])

        file_content = glob.glob(base_cache_directory + "tbo/master/*.txt")
        for rec in file_content:
            # open file
            filename = rec
            try:
                file = open(filename, 'r')
                country_file = json.loads(file.read())
                file.close()
            except:
                continue
            # loop per city ke fungsi get hotel giata
            for city in country_file:
                # for city in [{'code':'126632'}, {'code':'115936'}, {'code':'131408'}]:
                if city['name'].split(',')[0].lower() in rendered_city:
                    continue

                search_req = {
                    'provider': 'tbo',
                    'type': 'hotel',
                    'limit': '',
                    'offset': '',
                    'codes': city['code'],
                }
                hotel_fmt = []
                try:
                    hotel_objs = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                    # for hotel in hotel_objs['response'][1]:
                    #     try:
                    # TODO: Ambil image dkk
                    # search_req = {
                    #     'provider': 'tbo',
                    #     'type': 'hotel_detail',
                    #     'limit': '',
                    #     'offset': '',
                    #     'codes': hotel['id'],
                    # }
                    # hotel_fmt.append(hotel)
                    # except:
                    #     continue
                    hotel_fmt = hotel_objs[1]
                    length = len(hotel_fmt)
                    stopper = 0
                except:
                    length = -1
                    stopper += 1

                    if stopper == 7:
                        _logger.info("==================================")
                        _logger.info("= Stopped Because 7 error in row =")
                        _logger.info("==================================")
                        break
                # _logger.info("Get "+str(length)+" Hotel(s) for City: " + city + ', ' + rec[1])
                # need_to_add_list.append([i, city, rec[1], length])
                # filename = "/var/log/cache_hotel/tbo/" + city + ".json"

                _logger.info("Get " + str(length) + " Hotel(s) for City: " + city['name'] + ', ' + rec[32:-4])
                need_to_add_list.append([i, city['name'].split(',')[0], city['code'], rec[32:-4], length])
                filename = base_cache_directory + "tbo/" + city['name'].split(',')[0].replace('/', '-') + ".json"

                i += 1
                # Create Record Hotel per City
                file = open(filename, 'w')
                file.write(json.dumps(hotel_fmt))
                file.close()

                # Save per City
                with open(base_cache_directory + 'tbo/master_csv/result_data.csv', 'w') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerows(need_to_add_list)
                csvFile.close()
        _logger.info("===== Done =====")

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    def v2_collect_by_human_tbo(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
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
