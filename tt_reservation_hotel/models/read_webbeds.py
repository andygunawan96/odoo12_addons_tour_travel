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
    def v2_collect_by_system_webbeds(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        city_file_url = base_cache_directory + 'webbeds/00_other/dest_list.csv'
        api_context = {
            'co_uid': self.env.user.id
        }
        with open(city_file_url, 'r') as f:
            city_ids = csv.reader(f)
            a = 0
            last_render = self.env['ir.config_parameter'].sudo().get_param('hotel.city.rendered.list')
            try:
                last_render = json.loads(last_render)
                last_render_id = int(last_render[0])
            except:
                last_render_id = 0
            base_url = 'http://www.sunhotels.net/Sunhotels.net/HotelInfo/hotelImage.aspx'

            for rec in city_ids:
                a += 1
                if a < last_render_id:  # 19509
                    continue
                elif a % 31 == 0:
                    self.env['ir.config_parameter'].sudo().set_param('hotel.city.rendered.list', [a])
                    self.env.cr.commit()
                try:
                    # _logger.info("Processing (" + rec[2] + ").")
                    search_req = {
                        'provider': 'webbeds',
                        'type': 'hotel',
                        'limit': '',
                        'offset': '',
                        'codes': rec[1],
                    }
                    res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                    hotel_fmt_list = [{
                        'id': obj.get('hotel.id'),
                        'name': obj['name'],
                        'street': obj.get('hotel.addr.1') and str(obj['hotel.addr.1']) or '',
                        'street2': obj.get('hotel.addr.2') and str(obj['hotel.addr.2']) or '',
                        'street3': obj.get('hotel.address') and str(obj['hotel.address']) or '',
                        'description': obj.get('descriptions') and
                                       str(obj['descriptions'].get('hotel_information')) or '',
                        'email': '',
                        'images': obj['images'] and [
                            base_url + recs['fullSizeImage']['@url'] if recs.get('fullSizeImage') else
                            recs['smallImage']['@url'] for recs in
                            isinstance(obj['images']['image'], list) and obj['images'][
                                'image'] or [obj['images']['image']]] or [],
                        'facilities': obj['features'] and [
                            {'facility_id': '', 'url': '', 'facility_name': recs['@name'],
                             'description': 'VendorID:' + str(recs['@id'])} for recs in
                            isinstance(obj['features']['feature'], list) and
                            obj['features']['feature'] or [
                                obj['features']['feature']]] or [],
                        'phone': obj.get('phone') and obj['phone'] or '',
                        'fax': '',
                        'zip': obj.get('hotel.addr.zip') or '',
                        'website': '',
                        'lat': obj.get('coordinates') and obj['coordinates'].get('latitude') or '',
                        'long': obj.get('coordinates') and obj['coordinates'].get('longitude') or '',
                        'rating': obj.get('classification') and int(obj['classification'][0]) or 0,
                        'hotel_type': obj.get('type') or '',
                        'city': obj.get('destination') and str(obj['destination']) or '',
                    } for obj in res['response'][1]]

                    filename = base_cache_directory + "webbeds/" + rec[5]
                    if not os.path.isdir(filename):
                        os.makedirs(filename)
                    filename += '/' + rec[2] + ".json"
                    file = open(filename, 'w')
                    file.write(json.dumps(hotel_fmt_list))
                    file.close()
                    _logger.info(str(a) + ". Done City: " + rec[2] + ', ' + rec[5] + ' get: ' + str(len(hotel_fmt_list)) + ' Hotel(s)')
                    self.env.cr.commit()
                except Exception as e:
                    _logger.info("Error " + rec[2] + ': ' + str(e) + '.')
                    continue
        _logger.info("===== Done =====")
        return True

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    def v2_collect_by_human_webbeds(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        with open(base_cache_directory + '/webbeds_excel_pool/master_data/hotel_static_data.csv', 'r') as f:
            city_ids = csv.reader(f, delimiter=';')
            last_name = False
            # Mulai dari index 1 (Remove Header)
            # 0: Hotel ID
            # 1: Hotel name
            # 2: Country ID
            # 3: Country name
            # 4: Destination ID
            # 5: Destination name
            # 6: Resort ID
            # 7: Resort name
            # 8: Telephone
            # 9: Address
            # 10: Latitude
            # 11: Longitude
            # 12: Star Rating
            for rec in city_ids:
                if rec[0] == 'Hotel Id':
                    continue
                _logger.info("Processing (" + rec[1] + "): " + rec[5] + ", " + rec[7])
                if not last_name:
                    last_name = rec[5]
                    hotel_fmt_list = []

                hotel_fmt = {
                    'id': rec[0],
                    'name': rec[1],
                    'street': rec[9],
                    'street2': rec[7],
                    'street3': '',
                    'description': '',
                    'email': '',
                    'images': [],
                    'facilities': [],
                    'phone': rec[8],
                    'fax': '',
                    'zip': '',
                    'website': '',
                    'lat': rec[10],
                    'long': rec[11],
                    'rating': rec[12] and int(rec[12][0]) or 0,
                    'hotel_type': '',
                    'city': rec[5],
                }

                if last_name != rec[5]:
                    # Adriatic Coast / Rimini ==> Adriatic Coast - Rimini
                    last_name = last_name.replace('/', '-')
                    base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
                    filename = base_cache_directory + "webbeds_excel_pool/" + last_name + ".json"
                    file = open(filename, 'w')
                    file.write(json.dumps(hotel_fmt_list))
                    file.close()
                    _logger.info("Done City: " + last_name + ' get: ' + str(len(hotel_fmt_list)) + ' Hotel(s)')
                    last_name = rec[5]
                    hotel_fmt_list = []
                hotel_fmt_list.append(hotel_fmt)

        f.close()

    # 1c. Get Country Code
    def v2_get_country_code_webbeds(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        city_file_url = base_cache_directory + 'webbeds/00_other/dest_list.csv'
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_webbeds').id

        with open(city_file_url, 'r') as f:
            file_csv = csv.reader(f, delimiter=',')
            for data in file_csv:
                try:
                    data[0] = int(data[0]) #Remove Header table csv
                except:
                   continue
                if data[0] % 100 == 0:
                    _logger.info('Saving row number ' + str(data[0]))
                    self.env.cr.commit()
                _logger.info('Render ' + data[2] + ' Start')

                # Create external ID:
                old_obj = self.env['tt.provider.code'].search([('res_model', '=', 'tt.hotel.destination'), ('code', '=', data[1]), ('provider_id', '=', provider_id)])
                if not old_obj:
                    new_dict = {
                        'id': False,
                        'name': data[2],
                        'city_str': data[2],
                        'state_str': '',
                        'country_str': data[5],
                    }
                    is_exact, new_obj = self.env['tt.hotel.destination'].find_similar_obj(new_dict)
                    if not is_exact:
                        new_obj = self.env['tt.hotel.destination'].create(new_dict)
                        new_obj.fill_obj_by_str()
                        _logger.info('Create New Destination {} with code {}'.format(data[2], data[1]))
                    else:
                        _logger.info('Destination already Exist Code for {}, Country {}'.format(data[2], data[5]))

                    self.env['tt.provider.code'].create({
                        'res_model': 'tt.hotel.destination',
                        'res_id': new_obj.id,
                        'name': data[2] + ', ' + data[5],
                        'code': data[1],
                        'provider_id': provider_id,
                    })
                    _logger.info('Create External ID {} with id {}'.format(data[1], str(new_obj.id)))
                else:
                    _logger.info('External ID {} already Exist in {} with id {}'.format(data[1], old_obj.res_model, str(old_obj.res_id)))
                    old_obj.name = data[2] + ', ' + data[5]
        _logger.info('Render Done')
        return True


    # 1d. Get City Code
    def v2_get_city_code_webbeds(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        city_file_url = base_cache_directory + 'webbeds/00_other/dest_list.csv'
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_webbeds').id
        api_context = {
            'co_uid': self.env.user.id
        }
        search_req = {
            'provider': 'webbeds',
            'type': 'city',
            'limit': '',
            'offset': '',
            'codes': '',
        }
        resp = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        with open(city_file_url, 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(resp['response'][1])
        csvFile.close()
        _logger.info("===== Save to File Done =====")

        for data in resp['response'][1][1:]:
            if data[0] % 100 == 0:
                _logger.info('Saving row number ' + str(data[0]))
                self.env.cr.commit()
            _logger.info('Render ' + data[2] + ' Start')

            # Create external ID:
            old_obj = self.env['tt.provider.code'].search([('res_model', '=', 'tt.hotel.destination'), ('code', '=', data[1]), ('provider_id', '=', provider_id)])
            if not old_obj:
                new_dict = {
                    'id': False,
                    'name': data[2],
                    'city_str': data[2],
                    'state_str': '',
                    'country_str': data[5],
                }
                is_exact, new_obj = self.env['tt.hotel.destination'].find_similar_obj(new_dict)
                if not is_exact:
                    new_obj = self.env['tt.hotel.destination'].create(new_dict)
                    new_obj.fill_obj_by_str()
                    _logger.info('Create New Destination {} with code {}'.format(data[2], data[1]))
                else:
                    _logger.info('Destination already Exist Code for {}, Country {}'.format(data[2], data[5]))

                self.env['tt.provider.code'].create({
                    'res_model': 'tt.hotel.destination',
                    'res_id': new_obj.id,
                    'name': data[2],
                    'code': data[1],
                    'provider_id': provider_id,
                })
                _logger.info('Create External ID {} with id {}'.format(data[1], str(new_obj.id)))
            else:
                _logger.info('External ID {} already Exist in {} with id {}'.format(data[1], old_obj.res_model, str(old_obj.res_id)))
        _logger.info('Render Done')
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_webbeds(self):
        return True

    # 1f. Get Room Type Code
    def v2_get_room_code_webbeds(self):
        return True

    # 1g. Get Facility Code
    def v2_get_facility_code_webbeds(self):
        return True
