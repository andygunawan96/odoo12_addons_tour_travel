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
    def split_per_city(self, hotel_list, file_loc):
        hotel_per_city_dict = {}
        for hotel in hotel_list:
            try:
                city_name_fmt = hotel['location']['city'].strip().title().replace('/','-')
            except:
                city_name_fmt = 'Others'
            if not hotel_per_city_dict.get(city_name_fmt):
                hotel_per_city_dict[city_name_fmt] = []
            hotel_per_city_dict[city_name_fmt].append(hotel)

        if not os.path.exists(file_loc):
            os.makedirs(file_loc)

        for city, hotel_datas in hotel_per_city_dict.items():
            try:
                with open(file_loc + '/' + city + '.json', 'r') as f2:
                    record = f2.read()
                    record = json.loads(record)
                    hotel_datas = record + hotel_datas
                f2.close()
            except:
                # Hotel data does not exist
                pass
            file = open(file_loc + '/' + city + '.json', 'w')
            file.write(json.dumps(hotel_datas))
            file.close()
        return hotel_per_city_dict

    def get_data_form_file(self):
        master_loc = '/var/log/cache_hotel/traveloka/00_master/country/'
        for country_file in glob.glob(master_loc + "*.json"):
            file = open(country_file, 'r')
            hotel_list = json.loads(file.read())
            file.close()

            hotel_list = self.split_per_city(hotel_list, country_file[:-5])
        return True

    # Dari dari cassie 20210325
    def v2_collect_by_human_traveloka(self):
        workbook = xlrd.open_workbook('/var/log/cache_hotel/traveloka/00_master/Hotel List Inventory - Rodex.xlsx')
        # worksheet = workbook.sheet_by_name('Name of the Sheet')
        worksheet = workbook.sheet_by_index(0)
        # worksheet.nrows
        # worksheet.ncols

        mapped_hotel = {}
        # Result EXAMPLE: {'INDONESIA':{'JATIM':{'SURBAYA':[], 'MALANG':[],}}}
        for row in range(1, worksheet.nrows):
            code = worksheet.cell(row, 0).value
            name = worksheet.cell(row, 1).value
            country = worksheet.cell(row, 2).value
            region = worksheet.cell(row, 3).value
            city = worksheet.cell(row, 4).value
            address = worksheet.cell(row, 5).value
            lat = worksheet.cell(row, 6).value
            long = worksheet.cell(row, 7).value
            star = worksheet.cell(row, 8).value

            x = mapped_hotel
            try:
                for checked_data in [country, region, city]:
                    checked_data = checked_data.split('/')[0]
                    if not x.get(checked_data):
                        x[checked_data] = {}
                    x = x[checked_data]

                if mapped_hotel[country][region][city] == {}:
                    mapped_hotel[country][region][city] = []
                a = {
                    'id': int(code),
                    'name': name,
                    'street': address,
                    'street2': '',
                    'street3': city + ', ' + region + ', ' + country,
                    'description': '',
                    'email': '',
                    'images': [],
                    'facilities': [],
                    'phone': '',
                    'fax': '',
                    'zip': '',
                    'website': '',
                    'lat': str(lat),
                    'long': str(long),
                    'rating': int(star),
                    'hotel_type': '',
                    'city': city,
                }
                mapped_hotel[country][region][city].append(a)
            except:
                continue

        api_context = {
            'co_uid': self.env.user.id
        }
        API_CN_HOTEL.signin()
        base_url = '/var/log/cache_hotel/traveloka_file/'
        for country in mapped_hotel:
            new_url = base_url + country
            if not os.path.exists(new_url):
                os.makedirs(new_url)
            for region in mapped_hotel[country]:
                region_url = new_url + '/' + region
                if not os.path.exists(region_url):
                    os.makedirs(region_url)
                for city in mapped_hotel[country][region]:
                    limit = 100
                    objs = [int(x['id']) for x in mapped_hotel[country][region][city]]
                    for x in range(int(len(objs) / limit)+1):
                        code = [objs[x * limit:(x + 1) * limit],]
                        a = API_CN_HOTEL.get_record_by_api({
                            'provider': 'traveloka_hotel',
                            'type': 'property_details',
                            'limit': limit,
                            'offset': 1,
                            'codes': code,
                        }, api_context)

                        resp = a['response']
                        for hotel_obj in resp[list(resp.keys())[0]]:
                            for write_obj in mapped_hotel[country][region][city]:
                                if str(hotel_obj['id']) == str(write_obj['id']):
                                    try:
                                        # Create Image
                                        write_obj['images'] = hotel_obj['images']

                                        # Create Facility
                                        write_obj['facilities'] = hotel_obj['facilities']
                                        break
                                    except:
                                        _logger.info('Error Render: ' + str(hotel_obj['id']))
                                        break
                        self.env.cr.commit()

                    file = open(region_url + '/' + city + '.json', 'w')
                    file.write(json.dumps(mapped_hotel[country][region][city]))
                    file.close()
        return True

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
        # Check File Geo_list ada enggak
        # setiap geo_list

        # for type in ['geo_list', 'property_list']:
        for type in ['geo_list']:
            search_req = {
                'provider': 'traveloka_hotel',
                'type': type,
                'limit': 100,
                'offset': 100,
                'codes': ['ID', 'SG', 'MY', 'HK', 'TH', 'PH', 'VN', 'KH', 'LA'],
                # 'codes': ['ID',],
            }
            a = API_CN_HOTEL.get_record_by_api(search_req, api_context)
            # f2 = open('/var/log/tour_travel/traveloka_hotel/cache/2_AdminGW/edb093e3d658475394105f33926a1be8_VendorContent_geo_list_fmt_RESP_2.json','r')
            # f2 = f2.read()
            # catalog = json.loads(f2)
            # a = {
            #     'error_code': 0,
            #     'response': catalog
            # }
            # Save response list as CSV file:
            if not a['error_code'] == 0:
                _logger.info('Error during get ' + type + ' Error Msg:' + a['error_msg'])
                continue

            if type == 'property_list':
                limit = 100
                for rec in a['response'].keys():
                    hotel_ids = a['response'][rec]
                    for x in range(int(len(hotel_ids)/limit)):
                        code = [hotel_ids[x * limit:(x + 1) * limit],]
                        a = API_CN_HOTEL.get_record_by_api({
                            'provider': 'traveloka_hotel',
                            'type': 'property_details',
                            'limit': limit,
                            'offset': 1,
                            'codes': code,
                        }, api_context)

                        for dict_key, dict_value in a['response'].items():
                            _logger.info("Write File " + rec)
                            file_url = base_cache_directory + 'traveloka_api/' + rec
                            self.split_per_city(dict_value, file_url)
            else:
                for x in a['response'].keys():
                    if a['response'][x]:
                        header = list(a['response'][x][0].keys())
                        break
                need_to_add_list = [header]

                for rec in a['response'].values():
                    for data in rec:
                        need_to_add_list.append([data[x] for x in header])

                with open(base_cache_directory + 'traveloka_api/00_master/' + type + '.csv', 'w') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerows(need_to_add_list)
                csvFile.close()

    # untuk update dari excel ke data di backend tt.hotel
    def v2_get_hotel_image_traveloka(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        limit = 100
        api_context = {
            'co_uid': self.env.user.id
        }
        API_CN_HOTEL.signin()

        prov_traveloka_obj = self.env.ref('tt_reservation_hotel.tt_hotel_provider_traveloka')
        objs = self.env['tt.provider.code'].search([('res_model','=','tt.hotel'),('provider_id','=',prov_traveloka_obj.id)])
        for x in range(int(len(objs)/limit)):
            code = [[int(x1.code) for x1 in objs[x * limit:(x + 1) * limit]], ]
            a = API_CN_HOTEL.get_record_by_api({
                'provider': 'traveloka_hotel',
                'type': 'property_details',
                'limit': limit,
                'offset': 1,
                'codes': code,
            }, api_context)

            resp = a['response']
            for hotel_obj in resp[list(resp.keys())[0]]:
                try:
                    provider_code_obj = self.env['tt.provider.code'].search([('res_model','=','tt.hotel'),('code','=',hotel_obj['id'])])
                    create_hotel_id = self.env[provider_code_obj.res_model].browse(provider_code_obj.res_id)

                    is_exact, destination_id = self.env['tt.hotel.destination'].find_similar_obj({
                        'id': False,
                        'name': False,
                        'city_str': hotel_obj['location']['city'],
                        'state_str': hotel_obj['location']['state'],
                        'country_str': hotel_obj['location']['country'],
                    })
                    create_hotel_id.update({
                        'name': hotel_obj['name'],
                        'rating': hotel_obj['rating'],
                        'ribbon': hotel_obj['ribbon'],
                        'email': hotel_obj.get('email'),
                        'website': hotel_obj.get('website'),
                        'description': hotel_obj['description'],
                        'lat': hotel_obj['location'].get('latitude'),
                        'long': hotel_obj['location'].get('longitude'),
                        'phone': hotel_obj['phone'],
                        'address': hotel_obj['location']['address'],
                        'address2': False,
                        'address3': hotel_obj['location']['city'],
                        'zip': hotel_obj['location'].get('postal_code'),
                        'destination_id': destination_id,
                    })

                    # Create Image
                    create_hotel_id.image_ids = [(5,)]
                    for img in hotel_obj['images']:
                        img.update({
                            'hotel_id': create_hotel_id.id,
                            'provider_id': '',
                        })
                        self.env['tt.hotel.image'].create(img)

                    # Create Facility
                    fac_link_ids = []
                    for fac in hotel_obj['facilities']:
                        if fac.get('facility_id'):
                            fac_link_ids.append(int(fac['facility_id']))
                        else:
                            fac_link_ids.append(self.env['tt.hotel.facility'].sudo().find_by_name(fac.get('name','facility_name')))
                    create_hotel_id.update({'facility_ids': [(6, 0, fac_link_ids)]})
                except:
                    _logger.info('Error Render: ' + str(hotel_obj['id']))
                    continue

            self.env.cr.commit()
        return a

    # # untuk update dari excel ke cache
    # def v2_collect_by_system_traveloka(self):
    #     base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
    #     limit = 100
    #     api_context = {
    #         'co_uid': self.env.user.id
    #     }
    #     API_CN_HOTEL.signin()
    #
    #     prov_traveloka_obj = self.env.ref('tt_reservation_hotel.tt_hotel_provider_traveloka')
    #     objs = []
    #     for x in range(int(len(objs)/limit)):
    #         code = [[int(x1.code) for x1 in objs[x * limit:(x + 1) * limit]], ]
    #         a = API_CN_HOTEL.get_record_by_api({
    #             'provider': 'traveloka_hotel',
    #             'type': 'property_details',
    #             'limit': limit,
    #             'offset': 1,
    #             'codes': code,
    #         }, api_context)
    #
    #         resp = a['response']
    #         for hotel_obj in resp[list(resp.keys())[0]]:
    #             try:
    #                 # Create Image
    #                 x = hotel_obj['images']
    #
    #                 # Create Facility
    #                 x = hotel_obj['facilities']
    #             except:
    #                 _logger.info('Error Render: ' + str(hotel_obj['id']))
    #                 continue
    #         self.env.cr.commit()
    #     return a

    def v2_get_city_code_traveloka(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        country_file = base_cache_directory + 'traveloka_api/00_master/geo_list.csv'
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
                if row < 5990:  # Edit this value if render stop by other reason
                    continue

                name = body['name']
                code = body.get('geoId') or body.get('id')
                country_name = body.get('parentId') or False
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
