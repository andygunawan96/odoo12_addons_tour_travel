from odoo import api, fields, models, _
import json
import logging
from .ApiConnector_Hotel import ApiConnectorHotels
import csv, glob, os
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
    def v2_collect_by_system_hotelbeds(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_hotelbeds').id

        last_render_idx = self.env['ir.config_parameter'].sudo().get_param('last.gw.render.idx')
        last_render_idx = int(last_render_idx)
        hotel_resp = {}
        API_CN_HOTEL.signin()

        for country_codes in ['ID', 'MY', 'SG', 'TH', 'JP', 'CN', 'PH']:
            empty_resp = 0
            for x in range(300): #total 173000 hotel
                _logger.info("Requesting " + str((last_render_idx*1000) + 1) + " to " + str((last_render_idx+1)*1000))
                response = API_CN_HOTEL.get_record_by_api({'type': 'hotel', 'provider': 'hotelbeds', 'codes': country_codes, 'offset': (last_render_idx*1000) + 1, 'limit': (last_render_idx+1)*1000,})

                htl_len = len(response['response'][0])

                if htl_len == 0:
                    empty_resp += 1
                if empty_resp == 3:
                    last_render_idx = 0
                    _logger.info("Adding " + str(htl_len) + " Hotel(s)")
                    for x in hotel_resp.keys():
                        file_loc = base_cache_directory + 'hotelbeds/' + x
                        if not os.path.exists(file_loc):
                            os.makedirs(file_loc)
                        for y in hotel_resp[x].keys():
                            file_loc1 = file_loc + '/' + y
                            if not os.path.exists(file_loc1):
                                os.makedirs(file_loc1)
                            for z in hotel_resp[x][y].keys():
                                filename = file_loc1 + "/" + z.strip().split('/')[0] + ".json"
                                if os.path.exists(filename):
                                    with open(filename, 'r') as f2:
                                        record = f2.read()
                                        hotel_list_fmt = json.loads(record)
                                else:
                                    hotel_list_fmt = []
                                for body in hotel_resp[x][y][z]:
                                    try:
                                        hotel_list_fmt.append({
                                            'id': body['code'],
                                            'name': body['name']['content'],
                                            'street': body['address']['content'],
                                            'street2': '',
                                            'street3': body['city']['content'],  # body['destinationCode']
                                            'description': body['description']['content'] if body.get(
                                                'description') else '',
                                            'email': body.get('email'),
                                            'images': body.get('images'),
                                            'facilities': body.get('facilities'),
                                            'phone': ', '.join(
                                                [phon3['phoneType'] + ': ' + phon3['phoneNumber'] for phon3 in
                                                 body['phones']]) if body.get('phones') else '',
                                            'fax': '',
                                            'zip': body.get('postalCode'),
                                            'website': body.get('web'),
                                            'lat': body.get('coordinates') and body['coordinates']['latitude'] or '',
                                            'long': body.get('coordinates') and body['coordinates']['longitude'] or '',
                                            'rating': body['categoryCode'][0] if body.get('categoryCode') else 0,
                                            # 3EST
                                            'hotel_type': body.get('accommodationTypeCode'),
                                            'city': body['city']['content'],
                                        })
                                    except:
                                        _logger.info("Error Render " + body['name']['content'])
                                file = open(filename, 'w')
                                file.write(json.dumps(hotel_list_fmt))
                                file.close()
                    hotel_resp = {}
                    self.env['ir.config_parameter'].sudo().set_param('last.gw.render.idx', last_render_idx)
                    break

                _logger.info("Sent " + str((last_render_idx*1000) + 1) + " to " + str((last_render_idx+1)*1000) + " Return " + str(len(response['response'][0])))
                for hotel_loop in response['response'][0]:
                    if not hotel_resp.get(hotel_loop['countryCode']):
                        hotel_resp[hotel_loop['countryCode']] = {}
                    # if not hotel_resp[hotel_loop['countryCode']].get(hotel_loop['stateCode']):
                    #     hotel_resp[hotel_loop['countryCode']][hotel_loop['stateCode']] = {}
                    # if not hotel_resp[hotel_loop['countryCode']][hotel_loop['stateCode']].get(hotel_loop['city']['content'].lower()):
                    #     hotel_resp[hotel_loop['countryCode']][hotel_loop['stateCode']][hotel_loop['city']['content'].lower()] = []
                    if not hotel_resp[hotel_loop['countryCode']].get('W'):
                        hotel_resp[hotel_loop['countryCode']]['W'] = {}
                    if not hotel_resp[hotel_loop['countryCode']]['W'].get(hotel_loop['city']['content'].lower()):
                        hotel_resp[hotel_loop['countryCode']]['W'][hotel_loop['city']['content'].lower()] = []
                    hotel_resp[hotel_loop['countryCode']]['W'][hotel_loop['city']['content'].lower()].append(hotel_loop)

                if last_render_idx % 10 == 9:
                    _logger.info("Adding " + str(htl_len) + " Hotel(s)")
                    for x in hotel_resp.keys():
                        file_loc = base_cache_directory + 'hotelbeds/' + x
                        if not os.path.exists(file_loc):
                            os.makedirs(file_loc)
                        for y in hotel_resp[x].keys():
                            file_loc1 = file_loc + '/' + y
                            if not os.path.exists(file_loc1):
                                os.makedirs(file_loc1)
                            for z in hotel_resp[x][y].keys():
                                filename = file_loc1 + "/" + z.strip().split('/')[0] + ".json"
                                if os.path.exists(filename):
                                    with open(filename, 'r') as f2:
                                        record = f2.read()
                                        hotel_list_fmt = json.loads(record)
                                else:
                                    hotel_list_fmt = []
                                for body in hotel_resp[x][y][z]:
                                    try:
                                        hotel_list_fmt.append({
                                        'id': body['code'],
                                        'name': body['name']['content'],
                                        'street': body['address']['content'],
                                        'street2': '',
                                        'street3': body['city']['content'], #body['destinationCode']
                                        'description': body['description']['content'] if body.get('description') else '',
                                        'email': body.get('email'),
                                        'images': body.get('images'),
                                        'facilities': body.get('facilities'),
                                        'phone': ', '.join([phon3['phoneType'] + ': ' + phon3['phoneNumber'] for phon3 in body['phones']]) if body.get('phones') else '',
                                        'fax': '',
                                        'zip': body.get('postalCode'),
                                        'website': body.get('web'),
                                        'lat': body.get('coordinates') and body['coordinates']['latitude'] or '',
                                        'long': body.get('coordinates') and body['coordinates']['longitude'] or '',
                                        'rating': body['categoryCode'][0] if body.get('categoryCode') else 0, #3EST
                                        'hotel_type': body.get('accommodationTypeCode'),
                                        'city': body['city']['content'],
                                    })
                                    except:
                                        _logger.info("Error Render " + body['name']['content'])
                                file = open(filename, 'w')
                                file.write(json.dumps(hotel_list_fmt))
                                file.close()
                    hotel_resp = {}
                    self.env['ir.config_parameter'].sudo().set_param('last.gw.render.idx', last_render_idx)
                last_render_idx += 1
        return True

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    def v2_collect_by_human_hotelbeds(self):
        return True

    # 1c. Get Country Code
    def v2_get_country_code_hotelbeds(self):
        return True

    # 1d. Get City Code
    def v2_get_city_code_hotelbeds(self):
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_hotelbeds(self):
        return True

    # 1f. Get Room Type Code
    def v2_get_room_code_hotelbeds(self):
        return True

    # 1g. Get Facility Code
    def v2_get_facility_code_hotelbeds(self):
        return True
