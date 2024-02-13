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
    def v2_collect_by_system_knb(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        # params = self.env['ir.config_parameter'].sudo().get_param('hotel.city.rendered.list')
        # rendered_city = json.loads(params)
        #
        # API_CN_HOTEL.signin()
        # city_ids = glob.glob(base_cache_directory + "knb/*.json")
        #
        # for target_city in city_ids:
        #     target_city_name = target_city[25:-5]
        #     if target_city_name in rendered_city:
        #         continue
        #     with open(target_city, 'r') as f2:
        #         file = f2.read()
        #         hotel_ids = [rec['id'] for rec in json.loads(file)]
        #     f2.close()
        #     response = API_CN_HOTEL.send_request('get_hotel_detail', {'provider': ['knb'], 'codes': hotel_ids})
        #
        #     name = base_cache_directory + 'knb_api/' + target_city_name + ".json"
        #     file = open(name, 'w')
        #     file.write(json.dumps(response['response']['result']))
        #     file.close()
        #     rendered_city.append(target_city_name)
        #
        #     self.env['ir.config_parameter'].sudo().set_param('hotel.city.rendered.list', json.dumps(rendered_city))
        #     self.env.cr.commit()
        # self.env['ir.config_parameter'].sudo().set_param('hotel.city.rendered.list', json.dumps([]))

        # Part2: Update hotel RAW
        city_ids = glob.glob(base_cache_directory + "knb_api/*.json")
        for target_city in city_ids:
            target_city_name = target_city[29:-5]
            _logger.info("Processing: " + str(target_city_name))

            with open(target_city, 'r') as f2:
                file = f2.read()
                provider_codes = json.loads(file)
            f2.close()

            for code in provider_codes.keys():
                obj_id = self.env['tt.provider.code'].search([('code', '=', code), ('res_model', '=', 'tt.hotel')], limit=1)
                _logger.info("Processing Hotel with Code: " + str(code))
                if obj_id:
                    obj_id = obj_id[0].res_id
                    hotel_obj = self.env['tt.hotel'].browse(obj_id)
                    if not hotel_obj.lat and provider_codes[code]['lat']:
                        hotel_obj.lat = provider_codes[code]['lat']
                    if not hotel_obj.long and provider_codes[code]['long']:
                        hotel_obj.long = provider_codes[code]['long']
                    if not hotel_obj.website and provider_codes[code]['website']:
                        hotel_obj.website = provider_codes[code]['website']
                    if not hotel_obj.phone and provider_codes[code]['phone']:
                        hotel_obj.phone = provider_codes[code]['phone']
                    if not hotel_obj.facility_ids and provider_codes[code]['facility']:
                        for fac in provider_codes[code]['facility']:
                            # TODO hotel facility cari by provider code
                            fac_obj = self.env['tt.hotel.facility'].search([('name','=ilike', fac['name'])], limit=1)
                            if fac_obj and fac_obj[0].id not in hotel_obj.facility_ids.ids:
                                hotel_obj.facility_ids = [(4, fac_obj[0].id)]
                            else:
                                fac_type_id = self.env.ref('tt_reservation_hotel.hotel_facility_type_basic').id
                                fac_obj = self.env['tt.hotel.facility'].create({'name': fac['name'], 'facility_type_id': fac_type_id})
                                # TODO add provider code
                                hotel_obj.facility_ids = [(4, fac_obj.id)]
        _logger.info("===== Done =====")

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    # Todo: Perlu catat source data ne
    # def v2_collect_by_human_knb(self):
    def v2_collect_by_human_json_knb(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        need_to_add_list = [['No', 'City', 'Country', 'Hotel qty']]
        # Find all xls file in selected directory
        path = base_cache_directory + 'knb/00_master/'
        for country_file in glob.glob(os.path.join(path, '*.xls')):
            _logger.info("========================================")
            _logger.info("Write Country " + country_file.split('/')[-1].split('_')[2])
            _logger.info("========================================")
            # Baca file
            with open(country_file, 'r') as f:
                page = f.read()
                # File memang extension .xls
                # Ntah kenapa contain nya html page jadi mesti pake fungsi dibawah buat rubah jadi dict
                tree = html.fromstring(page)
                # rubah table excel jadi list of dict dengan key nya adalah line 1
                header = [rec.text for rec in tree.xpath('//tr')[0]]
                hotel_list = {}
                last_city = ''
                # dikasih len header supaya header tidak ikut di render
                for rec in tree.xpath('//tr')[1:]:
                    # if body['HotelCode'] == 'WSASTHBKK002130':
                    #     test = True
                    if len(rec.xpath('td')) == len(header):
                        body = {}
                        for idx, rec2 in enumerate(rec.xpath('td')):
                            body[header[idx]] = rec2.text if rec2.text != "" else ''
                        # Prepare dict to format cache
                        if not hotel_list.get(body['CityName']):
                            hotel_list[body['CityName']] = []
                        # if body['HotelCode'] == 'WSASIDSUB000138':
                        #     a = True
                        hotel_fmt = {
                            'id': body['HotelCode'],
                            'name': body['HotelName'],
                            'street': body['Address1'],
                            'street2': body['Address2'],
                            'street3': body['Address3'],
                            'description': body['Description'],
                            'email': body['Email'],
                            'images': [],
                            'facilities': [],
                            'phone': body['Telephone'],
                            'fax': body['Facsimile'],
                            'zip': body['Zipcode'],
                            'website': body['Website'],
                            'lat': '',
                            'long': '',
                            'rating': body['Rating'] or 0,
                            'hotel_type': '',
                            'city': body['CityName'],
                        }
                        hotel_list[body['CityName']].append(hotel_fmt)
                        last_city = body['CityName']
                    else:
                        # TODO Masuk kesini untuk kondisi descripsi atau facility lebih dari 1 TD sma Excel di split
                        # TODO Mungkin pikirkan supaya nilai dari facility / descripsi masih isa di lempar ke field yg lama
                        # hotel_list[last_city][-1]['description'] += ';;'
                        continue
            f.close()
            path = base_cache_directory + "knb/" + country_file.split('/')[-1].split('_')[2]
            if not os.path.isdir(path):
                os.makedirs(path)
            for city in hotel_list.keys():
                _logger.info("City: " + city + ' Get:' + str(len(hotel_list[city])) + 'Hotel(s)')
                filename = path + "/" + city.strip().split('/')[0] + ".json"
                file = open(filename, 'w')
                file.write(json.dumps(hotel_list[city]))
                file.close()

                need_to_add_list.append([1, city.encode("utf-8"),
                                         country_file.split('/')[-1].split('_')[2].encode("utf-8"),
                                         len(hotel_list[city])])

        with open(base_cache_directory + 'knb/00_result/Result.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

        _logger.info("========================================")
        _logger.info("             Write DONE                 ")
        _logger.info("========================================")

        return True

    def v2_collect_by_human_knb(self):
    # def v2_collect_by_human_csv_knb(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        need_to_add_list = [['No', 'City', 'Country', 'Hotel qty']]
        # Find all xls file in selected directory
        path = base_cache_directory + 'knb/00_master/'
        for country_file in glob.glob(os.path.join(path, '*.csv')):
            _logger.info("========================================")
            _logger.info("Write Country arc " + country_file.split('/')[-1].split('_')[2])
            _logger.info("========================================")
            # Baca file
            with open(country_file, 'r') as f:
                page = csv.reader(f, delimiter=':')
                # rubah table excel jadi list of dict dengan key nya adalah line 1
                hotel_list = {}
                header = []
                # dikasih len header supaya header tidak ikut di render
                for rec in page:
                    if not header:
                        header = rec
                        continue
                    body = {}
                    for idx, rec2 in enumerate(rec):
                        body[header[idx]] = rec2 or ''
                    if len(rec) != len(header) or not rec[0]:
                        desc_idx = False
                        for idx, oi in enumerate(header):
                            if oi == 'Description':
                                desc_idx = idx
                                break
                        if desc_idx:
                            hotel_list[last_city][-1]['description'] += ' ' + rec[desc_idx]
                        continue
                    # Prepare dict to format cache
                    if not hotel_list.get(body['CityName']):
                        hotel_list[body['CityName']] = []
                    # if body['HotelCode'] == 'WSASIDSUB000138':
                    #     a = True
                    hotel_fmt = {
                        'id': body['HotelCode'],
                        'name': body['HotelName'],
                        'street': body['Address1'],
                        'street2': body['Address2'],
                        'street3': body['Address3'],
                        'description': body['Description'],
                        'email': body['Email'],
                        'images': [],
                        'facilities': [],
                        'phone': body['Telephone'],
                        'fax': body['Facsimile'],
                        'zip': body['Zipcode'],
                        'website': body['Website'],
                        'lat': body.get('Latitude'),
                        'long': body.get('Longitude'),
                        'rating': body['Rating'] or 0,
                        'hotel_type': '',
                        'city': body['CityName'],
                    }
                    hotel_list[body['CityName']].append(hotel_fmt)
                    last_city = body['CityName']
            f.close()
            # Create Folder Country Here
            path = base_cache_directory + "knb/" + country_file.split('/')[-1].split('_')[2]
            if not os.path.isdir(path):
                os.makedirs(path)
            for city in hotel_list.keys():
                _logger.info("City: " + city + ' Get:' + str(len(hotel_list[city])) + ' Hotel(s)')
                filename = path + "/" + city.strip().split('/')[0] + ".json"

                # Read dulu file yg lama
                if os.path.isfile(filename):
                    with open(filename, 'r') as f:
                        file_content = f.read()
                        file_content = json.loads(file_content)
                        for hotel_data in hotel_list[city]:
                            is_new = True
                            for hotel_file_content in file_content:
                                if hotel_data['id'] == hotel_file_content['id']:
                                    is_new = False
                                    break
                            if is_new:
                                file_content.append(hotel_data)
                                _logger.info('Append New Hotel ' + hotel_data['name'])
                            else:
                                _logger.info('Skipping ' + hotel_data['name'] + ' (' + hotel_data['id'] + ') Already Exist')
                    hotel_list[city] = file_content

                file = open(filename, 'w')
                file.write(json.dumps(hotel_list[city]))
                file.close()

                need_to_add_list.append([1, city.encode("utf-8"),
                                         country_file.split('/')[-1].split('_')[2].encode("utf-8"),
                                         len(hotel_list[city])])

        with open(base_cache_directory + 'knb/result/Result.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()
        return True

    # 1c. Get Country Code
    def v2_get_country_code_knb(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        workbook = xlrd.open_workbook(base_cache_directory + 'knb/00_other/RODE_country_20201028120232.xls')
        # worksheet = workbook.sheet_by_name('Name of the Sheet')
        worksheet = workbook.sheet_by_index(0)
        # worksheet.nrows
        # worksheet.ncols
        a = []
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_knb').id
        for row in range(1, worksheet.nrows):
            name = worksheet.cell(row, 0).value
            code = worksheet.cell(row, 2).value

            country_obj = self.env['res.country'].find_country_by_name(name, 1)
            country_obj = country_obj and country_obj[0] or self.env['res.country'].create({'name': name})

            # Create external ID:
            if not self.env['tt.provider.code'].search([('res_model', '=', 'res.country'), ('res_id', '=', country_obj.id),
                                                        ('code', '=', code), ('provider_id', '=', provider_id)]):
                self.env['tt.provider.code'].create({
                    'res_model': 'res.country',
                    'res_id': country_obj.id,
                    'name': name,
                    'code': code,
                    'provider_id': provider_id,
                    'country_id': country_obj.id,
                })
        return a

    # 1d. Get City Code save in res.city
    def v2_get_city_code_knb1(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        workbook = xlrd.open_workbook(base_cache_directory + 'knb/00_other/RODE_city_20200307090456.xls')
        # worksheet = workbook.sheet_by_name('Name of the Sheet')
        worksheet = workbook.sheet_by_index(0)
        # worksheet.nrows
        # worksheet.ncols
        a = []
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_knb').id
        for row in range(1, worksheet.nrows):
            name = worksheet.cell(row, 0).value
            code = worksheet.cell(row, 2).value

            if row < 0: #Edit this value if render stop by other reason
                continue

            if row % 100 == 0:
                _logger.info('Saving row number ' + str(row))
                self.env.cr.commit()
            _logger.info('Render ' + name + ' Start')
            city_obj = self.env['res.city'].find_city_by_name(name, 1)
            if city_obj:
                city_obj = city_obj[0]
                _logger.info('Find Old Record')
            else:
                code_id = self.env['tt.provider.code'].search([('code','=', worksheet.cell(row, 5).value), ('provider_id','=', provider_id)])
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
                    'name': name,
                    'code': code,
                    'provider_id': provider_id,
                })
                _logger.info('Create New Code')
            else:
                _logger.info('Code already Exist Code')
            _logger.info('Render Done')
        return a

    # 1d. Get City Code save in tt.hotel.destination
    def v2_get_city_code_knb(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        for xls_sheet in ['RODE_city_111.xls',]:
            workbook = xlrd.open_workbook(base_cache_directory + 'knb/00_other/' + xls_sheet)
            # worksheet = workbook.sheet_by_name('Name of the Sheet')
            worksheet = workbook.sheet_by_index(0)
            # worksheet.nrows
            # worksheet.ncols
            a = []
            provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_knb').id
            for row in range(1, worksheet.nrows):
                name = worksheet.cell(row, 0).value
                code = worksheet.cell(row, 2).value
                # state_name = worksheet.cell(row, 0).value
                country_name = worksheet.cell(row, 3).value

                if row < 0:  # Edit this value if render stop by other reason
                    continue

                if row % 100 == 0:
                    _logger.info('Saving row number ' + str(row))
                    self.env.cr.commit()
                _logger.info('Render ' + name + ' Start')

                # Create external ID:
                old_obj = self.env['tt.provider.code'].search([('code', '=', code), ('provider_id', '=', provider_id)], limit=1)
                if not old_obj:
                    new_dict = {
                        'id': False,
                        'name': name + '; ' + country_name,
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
        _logger.info('Render Done')
        return a

    # 1e. Get Meal Code
    def v2_get_meal_code_knb(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        workbook = xlrd.open_workbook(base_cache_directory + 'knb/00_other/RODE_mealtype_20201028120355.xls')
        # worksheet = workbook.sheet_by_name('Name of the Sheet')
        worksheet = workbook.sheet_by_index(0)
        # worksheet.nrows
        # worksheet.ncols
        a = []
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_knb').id
        for row in range(1, worksheet.nrows):
            name = worksheet.cell(row, 1).value
            code = worksheet.cell(row, 0).value

            meal_obj = self.env['tt.meal.type'].search([('name','=ilike', name)], limit=1)
            if meal_obj:
                meal_obj = meal_obj[0]
            else:
                meal_obj = self.env['tt.meal.type'].create({'name': name,})

            # Create external ID:
            if not self.env['tt.provider.code'].search([('res_model', '=', 'tt.meal.type'), ('res_id', '=', meal_obj.id),
                                                        ('code', '=', code), ('provider_id', '=', provider_id)]):
                self.env['tt.provider.code'].create({
                    'res_model': 'tt.meal.type',
                    'res_id': meal_obj.id,
                    'name': name,
                    'code': code,
                    'provider_id': provider_id,
                })
        return a

    # 1f. Get room Code
    # Note: Dari KNB waktu search sdha dikasih room caateg beserta deskripsi nya jadi bisa di skip bagian ini
    # Note: Blum ku code
    def v2_get_room_code_knb(self):
        return True
        # base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        # workbook = xlrd.open_workbook(base_cache_directory + 'knb/00_other/RODE_roomcat_20201028120323.xls')
        # # worksheet = workbook.sheet_by_name('Name of the Sheet')
        # worksheet = workbook.sheet_by_index(0)
        # # worksheet.nrows
        # # worksheet.ncols
        # a = []
        # provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_knb').id
        # for row in range(1, worksheet.nrows):
        #     name = worksheet.cell(row, 1).value
        #     code = worksheet.cell(row, 0).value
        # #Need to code start Here
        #     meal_obj = self.env['tt.meal.type'].search([('name', '=ilike', name)], limit=1)
        #     if meal_obj:
        #         meal_obj = meal_obj[0]
        #     else:
        #         meal_obj = self.env['tt.meal.type'].create({'name': name, })
        #
        #     # Create external ID:
        #     if not self.env['tt.provider.code'].search(
        #             [('res_model', '=', 'tt.meal.type'), ('res_id', '=', meal_obj.id),
        #              ('code', '=', code), ('provider_id', '=', provider_id)]):
        #         self.env['tt.provider.code'].create({
        #             'res_model': 'tt.meal.type',
        #             'res_id': meal_obj.id,
        #             'name': name,
        #             'code': code,
        #             'provider_id': provider_id,
        #         })
        # return a

    # 1g. Get Facility Code
    def v2_get_facility_code_knb(self):
        return True

    # 2a. Get Hotel Image
    def v2_get_hotel_image_knb(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        for city_id in [797, 644, 712]:
            # city_obj = self.env['res.city'].browse(694)
            hotel_objs = self.env['tt.hotel'].search([('city_id','=', city_id),('provider','ilike','klik and book'),('image_ids','=',False)])
            const = 3
            for idx in range(math.ceil(len(hotel_objs)/const)):
                # if idx < 105:
                #     continue
                start = idx * const
                end = (idx + 1) * const
                _logger.info('Render ' + str(start) + ' to ' + str(end))
                search_req = {
                    'provider': 'knb',
                    'type': 'GetImageList',
                    'limit': '',
                    'offset': '',
                    'codes': [(rec.id, rec.name) for rec in hotel_objs[start:end]],
                }
                try:
                    a = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                    for hotel_resp in a['response']:
                        for img in a['response'][hotel_resp]:
                            self.env['tt.hotel.image'].create({
                                'url': img,
                                'hotel_id': int(hotel_resp),
                            })
                except:
                    a = False

                if idx % 5 == 0:
                    _logger.info('======= Saving #' + str((idx+1) * const) + '/' + str(len(hotel_objs)) + ' =======')
                    self.env.cr.commit()
        _logger.info('================================')
        _logger.info('========== Proses End ==========')
        _logger.info('================================')