from odoo import api, fields, models, _
import json
import logging
import xlrd
from .ApiConnector_Hotel import ApiConnectorHotels
import csv, glob, os
from lxml import html
from ...tools import xmltodict
import csv
import math

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
    def v2_collect_by_system_traveloka(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        api_context = {
            'co_uid': self.env.user.id
        }
        API_CN_HOTEL.signin()
        # for type in ['geo_list', 'property_list']:
        for type in ['geo_list']:
            search_req = {
                'provider': 'traveloka_hotel',
                'type': type,
                'limit': 100,
                'offset': 100,
                # 'codes': ['ID', 'PH', 'SG', 'MY', 'VN'],
                'codes': ['ID',],
            }
            a = API_CN_HOTEL.get_record_by_api(search_req, api_context)

            # Save response list as CSV file:
            if not a['error_code'] == 0:
                _logger.info('Error during get ' + type + ' Error Msg:' + a['error_msg'])
                continue
            for x in a['response'].keys():
                if a['response'][x]:
                    header = list(a['response'][x][0].keys())
                    break
            need_to_add_list = [ header ]
            if type == 'property_list':
                for dict_key, dict_value in a['response'].items():
                    _logger.info("Write File " + dict_key)
                    dict_value = dict_value
                    for city_name, city_result in dict_value:
                        filename1 = base_cache_directory + 'traveloka/00_master/country/' + dict_key + '/' + city_name + ".json"
                        file = open(filename1, 'w')
                        file.write(json.dumps(city_result))
                        file.close()
            else:
                for rec in a['response'].values():
                    for data in rec:
                        need_to_add_list.append([data[x] for x in header])

                with open(base_cache_directory + 'traveloka/00_master/' + type + '.csv', 'w') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerows(need_to_add_list)
                csvFile.close()

    def v2_get_city_code_traveloka(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        country_file = base_cache_directory + 'traveloka/00_master/geo_list.csv'
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_traveloka').id
        with open(country_file, 'r') as f:
            page = csv.reader(f, delimiter=',')
            # rubah table excel jadi list of dict dengan key nya adalah line 1
            hotel_list = {}
            header = []
            # dikasih len header supaya header tidak ikut di render
            for row, rec in enumerate(page):
                if not header:
                    header = rec
                    continue
                body = {}
                for idx, rec2 in enumerate(rec):
                    body[header[idx]] = rec2 or ''
                if row < 0:  # Edit this value if render stop by other reason
                    continue

                name = body['name']
                code = body['geoId']
                country_name = body['parentId']
                if row % 100 == 0:
                    _logger.info('Saving row number ' + str(row))
                    self.env.cr.commit()
                _logger.info('Render ' + name + ' Start')

                # Create external ID:
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
                        'name': name,
                        'code': code,
                        'provider_id': provider_id,
                    })
                    _logger.info('Create External ID {} with id {}'.format(code, str(new_obj.id)))
                else:
                    _logger.info('External ID {} already Exist in {} with id {}'.format(code, old_obj.res_model, str(old_obj.res_id)))
        f.close()
        _logger.info('Render Done')
