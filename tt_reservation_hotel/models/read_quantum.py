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
    def v2_collect_by_system_quantum(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }
        with open(base_cache_directory + 'quantum/master/city_code.csv', 'r') as f:
            city_ids = csv.reader(f, delimiter=';')
            for idx, rec in enumerate(city_ids):
                # if idx == 0:
                if idx < 1003:
                    continue
                search_req = {
                    'provider': 'quantum',
                    'type': 'city_api',
                    'limit': '0',
                    'offset': '0',
                    'codes': rec[1] + '~' + rec[0],
                }

                res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                if res['error_code'] != 0:
                    raise ('Error')
                else:
                    hotel_fmt_objs = []
                    for obj in res['response'].get('hotels'):
                        obj.update({
                            'address': obj['location']['address'],
                            'lat': obj['location']['latitude'],
                            'long': obj['location']['longitude'],
                            'city': rec[2],
                            'country': obj['location']['country'],
                        })

                        for fac in obj['facilities']:
                            fac['facility_name'] = fac.pop('name')

                        obj.pop('hotel_code')
                        obj.pop('prices')
                        obj.pop('location')
                        hotel_fmt_objs.append(obj)
                    if hotel_fmt_objs:
                        self.file_log_write(str(idx) + '. Hotel found for ' + rec[2] + ': ' + str(len(hotel_fmt_objs)))
                        try:
                            # Langsung Compare
                            with open(base_cache_directory + 'quantum/' + rec[2].replace('/', ' ') + '.json',
                                      'r') as f2:
                                file = f2.read()
                                hotel_in_file = json.loads(file)
                                for hotel_fmt in hotel_fmt_objs:
                                    # Cek apakah file dengan kota tsb sdah ada di memory?
                                    same_name = list(filter(lambda x: x['name'] == hotel_fmt['name'], hotel_in_file))
                                    if same_name:
                                        # tambahkan detail ke record yg sama tersebut
                                        same_name[0]['images'] = hotel_fmt['images']
                                        same_name[0]['facilities'] = hotel_fmt['facilities']
                                        self.file_log_write('Sync: ' + hotel_fmt['name'])
                                    else:
                                        # create baru di memory
                                        hotel_in_file.append(hotel_fmt)
                                        self.file_log_write('New : ' + hotel_fmt['name'])
                            f2.close()
                        except:
                            # Simpan di Folder sendiri
                            self.file_log_write('Creating new Folder')
                            with open(base_cache_directory + 'quantum/' + rec[2].replace('/', ' ') + '.json',
                                      'w+') as f:
                                self.file_log_write(
                                    str(idx) + '. Hotel found for ' + rec[2] + ': ' + str(len(hotel_fmt_objs)))
                                f.write(json.dumps(hotel_fmt_objs))
                            hotel_in_file = hotel_fmt_objs

                        self.file_log_write('Total hotel for ' + rec[2] + ': ' + str(len(hotel_in_file)))
                        with open(base_cache_directory + 'quantum/' + rec[2].replace('/', ' ') + '.json', 'w+') as f:
                            f.write(json.dumps(hotel_in_file))

                    else:
                        self.file_log_write(str(idx) + '. No Hotel Found for ' + rec[2])
        f.close()
        _logger.info("===== Done =====")

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    # CSV data Adrian Quantum
    def v2_collect_by_human_quantum(self):
        hotel_fmt_list = {}
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        with open(base_cache_directory + 'quantum_pool/master/Hotels20200728.csv', 'r') as f:
            hotel_ids = csv.reader(f, delimiter=';')
            for obj in hotel_ids:
                add = obj[2]
                add += ', ' + obj[3] if len(obj[3]) > 1 else ''
                add += ', ' + obj[4] if len(obj[4]) > 1 else ''
                # Formatting Hotel
                hotel_fmt_obj = {
                    'id': obj[0],
                    'name': obj[1],
                    'street': add,
                    # 'address2': obj[3],
                    # 'address3': obj[4],
                    'description': 'Rail:' + obj[14] + ' Distance: ' + obj[15] or '' if obj[14] else '',
                    'email': obj[11],
                    'images': [],
                    'facilities': [],
                    'phone': obj[17],
                    'fax': obj[18],
                    'zip': obj[8],
                    'website': '',
                    'lat': obj[23],
                    'long': obj[24],
                    'rating': obj[21] and obj[21][0] or '',
                    'street2': 'City: ' + obj[25] + '; Country: ' + obj[7] or '',
                    'city': obj[25].capitalize(),
                }
                if not hotel_fmt_list.get(obj[25].capitalize()):
                    hotel_fmt_list[obj[25].capitalize()] = []
                # Add Hotel ke Dict
                hotel_fmt_list[obj[25].capitalize()].append(hotel_fmt_obj)
        f.close()
        need_to_add_list = [['No', 'Name', 'Hotel QTY']]
        self.file_log_write('###### Render Start ######')
        # Untuk setiap Key Loop
        for idx, city in enumerate(hotel_fmt_list.keys()):
            self.file_log_write("Write File " + city + " found : " + str(len(hotel_fmt_list[city])) + ' Hotel(s)')
            need_to_add_list.append([idx + 1, city, len(hotel_fmt_list[city])])
            filename = base_cache_directory + "quantum_pool/" + city.split('/')[0] + ".json"
            file = open(filename, 'w')
            file.write(json.dumps(hotel_fmt_list[city]))
            file.close()
        self.file_log_write('###### Render END ######')
        with open(base_cache_directory + 'quantum_pool/master/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()
        _logger.info("===== Done =====")

    # 1c. Get Country Code
    def v2_get_country_code_quantum(self):
        return True

    # 1d. Get City Code save in tt.hotel.destination
    def v2_get_city_code_quantum(self):
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_quantum(self):
        return True

    # 1f. Get room Code
    def v2_get_room_code_quantum(self):
        return True

    # 1g. Get Facility Code
    def v2_get_facility_code_quantum(self):
        return True
