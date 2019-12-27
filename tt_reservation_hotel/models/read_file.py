from odoo import api, fields, models, _
import json
import logging
from .ApiConnector_Hotel import ApiConnectorHotels
import csv, glob, os
from lxml import html
from ...tools import xmltodict

_logger = logging.getLogger(__name__)
API_CN_HOTEL = ApiConnectorHotels()


class HotelInformation(models.Model):
    _inherit = 'tt.hotel'

    # HotelsPro
    def get_record_by_file(self, url, filename, number, extension, provider_id):
        # url = '/home/rodex-it-05/Documents/VIN/Document/Hotel/Api./HotelPro/consumer-20180423-export/'
        # filename = 'hotels-'
        # filename = 'countries-'
        # filename = 'destinations-'
        # number = 420
        # extension = '.json'
        # provider_id = 2267

        state = 'done'
        while number:
            try:
                _logger.info("Opening file (%s)." % url + filename + str(number-1))
                with open(url + filename + str(number-1) + extension) as f:
                    data = json.load(f)
                    # Hotel Done
                    if filename == 'hotels-':
                        for rec in data:
                            hotel_id = self.env['tt.hotel'].search([('name', '=', rec.get('name') or '')], limit=1)
                            if not hotel_id:
                                hpc_id = self.env['provider.code'].search([('code', '=', str(rec['destination']) ), ('city_id', '!=', False)], limit=1)
                                vals = {
                                    'street': rec.get('address',''),
                                    # 'address': rec['code'], #'Provider Code: 1f3493'
                                    # 'country_id': rec['country'], #'rs'
                                    'email': rec.get('email',''),
                                    # 'hotel_type_id': rec['hotel_type'],
                                    'hotel_partner_city_id': hpc_id and hpc_id.city_id.id or 0,
                                    # 'facility_ids': [],
                                    # 'images': [],
                                    'phone': rec.get('phone',''),
                                    'lat': rec.get('latitude',''),
                                    'long': rec.get('longitude',''),
                                    'name': rec.get('name') or '',
                                    'rating': rec.get('stars') and (rec['stars'] > 7 and 5 or int(rec['stars'])) or 0,
                                    'zip': rec.get('zipcode',''),
                                    'description': rec.get('descriptions') and rec['descriptions'].get('hotel_information') or '',
                                    'hotel_partner_id': 2262,
                                    'tac': rec.get('destination') or ' ',
                                }
                                hotel_id = self.env['tt.hotel'].create(vals)

                                hotel_id.tac += ', ' + filename + str(number-1) + extension
                                self.env['provider.code'].create({
                                    'hotel_id': hotel_id.id,
                                    'code': rec['code'],
                                    'name': rec.get('name') or '',
                                    'provider_id': provider_id,
                                })

                                if rec.get('hotel_type'):
                                    code_id = self.env['provider.code'].search([('code', '=', rec['hotel_type']),
                                                                                ('type_id', '!=', False),
                                                                                ('provider_id', '=', provider_id)], limit=1)
                                    hotel_id.hotel_type_id = code_id and code_id[0].type_id.id or ''

                                if rec.get('images'):
                                    for image in rec['images']:
                                        image_url_complete = image['original'] or image['thumbnail_images'].get('large', 'mid')
                                        image_small = image['thumbnail_images'].get('mid', 'small') or image['original']

                                        self.env['product.image'].create({
                                            'hotel_id': hotel_id.id,
                                            'name': image['tag'],
                                            'image_url_complete': image_url_complete.encode('utf-8'),
                                            'image_small': image_small.encode('utf-8'),
                                        })

                                if rec.get('facilities'):
                                    temp_str = ''
                                    for fac in rec['facilities']:
                                        fac_id = self.env['provider.code'].search([('code','=',fac),('facility_id','!=',False),
                                                                            ('provider_id','=',provider_id)], limit=1)
                                        if fac_id:
                                            hotel_id.facility_ids = [(4, fac_id[0].facility_id.id)]
                                        else:
                                            temp_str += fac['code']
                                    hotel_id.tac += temp_str and 'Facility:' + temp_str or ''
                            else:
                                hotel_id.tac = rec.get('destination') or ' '
                                hotel_id.tac += ', ' + filename + str(number - 1) + extension

                                provider_code = self.env['tt.hotel'].get_provider_code(hotel_id.id, provider_id)
                                if provider_code and provider_code != rec['code'] or 1 == 1:
                                    self.env['provider.code'].create({
                                        'hotel_id': hotel_id.id,
                                        'code': rec['code'],
                                        'name': rec.get('name') or '',
                                        'provider_id': provider_id,
                                    })
                            self.env.cr.commit()
                    # Country DONE
                    elif filename == 'countries-':
                        for rec in data:
                            country_id = self.env['res.country'].search(['|', ('name','ilike',rec['name']), ('code','=',rec['code'])], limit=1)
                            if country_id:
                                self.env['provider.code'].create({
                                    'country_id': country_id.id,
                                    'name': rec['name'],
                                    'code': rec['code'],
                                    'provider_id': provider_id,
                                })
                            self.env.cr.commit()
                    # Destinations
                    elif filename == 'destinations-':
                        for rec in data:
                            city_id = self.env['res.country.city'].search([('name','=',rec['name'])], limit=1)
                            if not city_id:
                                city_id = self.env['res.country.city'].search([('name', 'ilike', rec['name'])], limit=1)
                            if city_id:
                                self.env['provider.code'].create({
                                    'city_id': city_id.id,
                                    'name': rec['name'],
                                    'code': rec['code'],
                                    'provider_id': provider_id,
                                })
                            self.env.cr.commit()
                    # Facilities
                    elif filename == 'facilities-':
                        for rec in data:
                            code_id = self.env['provider.code'].search([('code','=',rec['code']),('facility_id','!=',False),
                                                                            ('provider_id','=',provider_id)], limit=1)
                            if code_id:
                                code_id[0].update({'name': rec['name']})
                            else:
                                facility_id = self.env['tt.hotel.facility'].search([('name','=',rec['name'])], limit=1)
                                if not facility_id:
                                    facility_id = self.env['tt.hotel.facility'].create({
                                        'name': rec['name'],
                                        'description': rec['name'],
                                        'facility_type_id': 1,
                                    })
                                self.env['provider.code'].create({
                                    'name': rec['name'],
                                    'facility_id': facility_id.id,
                                    'code': rec['code'],
                                    'provider_id': provider_id,
                                })
                            self.env.cr.commit()
                    # Hotel Type
                    elif filename == 'hoteltypes-':
                        for rec in data:
                            code_id = self.env['provider.code'].search(
                                [('code', '=', rec['code']), ('type_id', '!=', False), ('provider_id', '=', provider_id)], limit=1)
                            if code_id:
                                code_id[0].update({'name': rec['name']})
                            else:
                                type_id = self.env['tt.hotel.type'].search([('name', '=', rec['name'])], limit=1)
                                if not type_id:
                                    type_id = self.env['tt.hotel.type'].create({
                                        'name': rec['name'],
                                        'description': rec['name'],
                                    })
                                self.env['provider.code'].create({
                                    'name': rec['name'],
                                    'type_id': type_id.id,
                                    'code': rec['code'],
                                    'provider_id': provider_id,
                                })
                            self.env.cr.commit()
                number += 1
            except IOError as e:
                _logger.error("Couldn't open or write to file (%s)." % e)
                state = 'error'
                break
        return state, number

    # HotelsPro:
    # Step 01: Ambil smua master(hotel_type, fac, country, destinations)
    # Step 1a: Simpan dalam bentuk File
    def get_record_by_file_2(self):
        url = '/home/rodex-it-05/Documents/VIN/Document Vendor Hotel, Payment GW/Api./HotelPro/01_DEV/Data/consumer-20190624-export/'

        cache_hotel = {}
        type = {}
        filenames = ['hoteltypes-', 'facilities-', 'country-']
        for filename in filenames:
            number = 1
            while number:
                try:
                    _logger.info("Opening file (" + url + filename + str(number-1) +").")
                    with open(url + filename + str(number-1) + '.json') as f:
                        data = json.load(f)
                        for rec in data:
                            type[rec['code']] = rec['name']
                    number += 1
                except IOError as e:
                    _logger.error("Couldn't open or write to file (%s)." % e)
                    cache_hotel[filename[:-1]] = type
                    break

        filename = "/var/log/tour_travel/file_hotelspro_master/master_info.txt"
        file = open(filename, 'w')
        file.write(json.dumps(cache_hotel))
        file.close()

    def get_record_by_file_2a(self):
        url = '/home/rodex-it-05/Documents/VIN/Document Vendor Hotel, Payment GW/Api./HotelPro/01_DEV/Data/consumer-20190624-export/'

        cache_hotel = {}
        filenames = ['destinations-',]
        for filename in filenames:
            number = 1
            while number:
                try:
                    _logger.info("Opening file (" + url + filename + str(number-1) +").")
                    with open(url + filename + str(number-1) + '.json') as f:
                        data = json.load(f)
                        for rec in data:
                            cache_hotel[rec['code']] = rec['name']
                    number += 1
                except IOError as e:
                    _logger.error("Couldn't open or write to file (%s)." % e)
                    break

        filename = "/var/log/tour_travel/file_hotelspro_master/master_dest.txt"
        file = open(filename, 'w')
        file.write(json.dumps(cache_hotel))
        file.close()

    # HotelsPro: Read smua file hotel dan map per city
    def get_record_by_file_3(self):
        # Step 1b: Load cache
        with open("/var/log/tour_travel/file_hotelspro_master/master_info.txt") as f:
            cache_data = json.load(f)
            cache_type = cache_data['hoteltypes']
            cache_fac = cache_data['facilities']
            cache_country = cache_data['country']
        f.close()
        # Step 02: Buat smua file dari city
        with open("/var/log/tour_travel/file_hotelspro_master/master_dest.txt") as f:
            cache_city = json.load(f)
        f.close()
        # Step 03: Loop untuk smua file hotel
        # Step 04: mapping berdasarkan city
        url = '/home/rodex-it-05/Documents/VIN/Document Vendor Hotel, Payment GW/Api./HotelPro/01_DEV/Data/consumer-20190624-export/'

        cache_hotel = {}
        filename = 'hotels-'
        number = 1
        while number:
            try:
                _logger.info("Opening file (" + filename + str(number - 1) + ").")
                with open(url + filename + str(number - 1) + '.json') as f:
                    data = json.load(f)
                    for obj in data:
                        city_name = cache_city[obj.get('destination')].replace('/','-').replace("\'",'-').encode("utf-8") or ''
                        if not cache_hotel.get(city_name):
                            cache_hotel[city_name] = []
                        # _logger.info("Process: " + json.dumps(obj))
                        cache_hotel[city_name].append({
                            'id': obj.get('code'),
                            'name': obj['name'].encode("utf-8"),
                            'street': obj.get('address') and obj['address'].encode("utf-8") or '',
                            'description': obj.get('descriptions') and obj['descriptions'].get('hotel_information').encode("utf-8"),
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
                            'hotel_type': obj.get('hotel_type') and cache_type[obj['hotel_type']] or '',
                            'city': city_name,
                        })
                    if number % 3 == 0:
                        for rec in cache_hotel.keys():
                            temp_filename = "/var/log/tour_travel/hotelspro_file/" + rec + ".json"
                            try:
                                with open(temp_filename, 'r') as f2:
                                    a = f2.read()
                                    old_record = json.loads(a)
                                    old_record += cache_hotel[rec]
                                f2.close()
                            except:
                                old_record = cache_hotel[rec]

                            file = open(temp_filename, 'w+')
                            file.write(json.dumps(old_record))
                            file.close()
                        cache_hotel = {}
                number += 1
            except IOError as e:
                _logger.error("Couldn't open or write to file (%s)." % e)
                for rec in cache_hotel.keys():
                    filename = "/var/log/tour_travel/hotelspro_file/" + rec + ".json"
                    try:
                        with open(temp_filename, 'r') as f2:
                            a = f2.read()
                            old_record = json.loads(a)
                            old_record += cache_hotel[rec]
                        f2.close()
                    except:
                        old_record = cache_hotel[rec]
                    file = open(filename, 'w')
                    file.write(json.dumps(old_record))
                    file.close()
                break

    # Hotelspro: Tools untuk hitung jumlah hotel per city dan kelengkapan data nya
    def get_record_by_file_4(self):
        with open("/var/log/tour_travel/file_hotelspro_master/master_dest.txt") as f:
            cache_city = json.load(f)
        f.close()
        need_to_add_list = [['No', 'Name', 'Hotel QTY', 'Hv Images', 'Hv Facilities', 'Hv Rating', 'Img Ratio',
                             'Fac Ratio', 'Rating Ratio']]
        for dest_name in cache_city:
            temp_filename = "/var/log/tour_travel/hotelspro_file/" + cache_city[dest_name] + ".json"
            try:
                _logger.info("Opening file (" + temp_filename + ").")
                with open(temp_filename, 'r') as f2:
                    try:
                        a = f2.read()
                        record = json.loads(a)
                        hotel_qty = len(record)
                        hotel_img = hotel_fac = hotel_rating = 0
                        for rec in record:
                            hotel_img += rec['images'] and 1 or 0
                            hotel_fac += rec['facilities'] and 1 or 0
                            hotel_rating += rec['rating'] and 1 or 0
                        need_to_add_list.append([1, cache_city[dest_name].encode("utf-8"), hotel_qty,
                                                 hotel_img, hotel_fac, hotel_rating, float(hotel_img/hotel_qty),
                                                 float(hotel_fac/hotel_qty), float(hotel_rating/hotel_qty)])
                    except:
                        need_to_add_list.append([1, cache_city[dest_name].encode("utf-8"), 'error',
                                                 0, 0, 0, 0, 0, 0])
                f2.close()
            except:
                need_to_add_list.append([1, cache_city[dest_name].encode("utf-8"), 'Not Found', 0, 0, 0, 0, 0, 0])

        with open('/var/log/tour_travel/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    def rec_to_images(self, recs):
        vals = []
        try:
            for rec in recs:
                obj = self.env['product.image'].create({
                    'sequence': rec.get('order') or 20,
                    'name': 'Characteristic Code: ' + rec.get('characteristicCode') or '-' + '; imageTypeCode: ' + rec.get('imageTypeCode')  or '-',
                    'image_url_complete': rec.get('path'),
                    'description': 'RoomCode: ' + rec.get('roomCode') or '-' + '; RoomType: ' + rec.get('roomType') or '-',
                })
                vals.append(obj.id)
        except:
            return vals
        return vals

    def rec_to_images2(self, recs):
        vals = []
        try:
            for rec in recs:
                obj = self.env['product.image'].create({
                    'sequence': 20,
                    'name': rec.get('Caption', 'None') + '~' + rec.get('Type', 'None'),
                    'image_url_complete': rec.get('URL'),
                    'description': '',
                })
                vals.append(obj.id)
        except:
            return vals
        return vals

    def rec_to_tac(self, recs):
        vals = []
        val = ''
        try:
            for rec in recs:
                if rec.get('Category'):
                    val += 'Category: ' + rec.get('Category')
                if rec.get('Start'):
                    val += 'Apply on: ' + rec.get('Start')
                    if rec.get('End'):
                        val += 'Until: ' + rec.get('End')
                val += rec.get('Text')
                vals.append(val)
        except:
            return vals
        return vals

    # HotelBeds
    def get_record_by_api(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        search_req = {
            'provider': 'hotelbeds',
            # 'countryCodes': 'ID',
            # 'type': 'country',
            # 'type': 'destination',
            'type': 'hotel',
            'limit': '1000',
            'offset': '501',
        }

        res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        if res['error_code'] != 0:
            raise ('Error')
        else:
            provider_id = self.env['res.partner'].search([('is_master_vendor', '=', True),('provider_code', '=', search_req['provider'])], limit=1)
            for obj_list in res.get('response'):
                for obj in isinstance(obj_list, list) and obj_list or [obj_list]:
                    if obj.get('description') and search_req['type'] == 'destination':
                        vals = {
                            'name': obj.get('description').get('content'),
                            'code': obj['code'],
                            'provider_id': provider_id[0].id,
                        }
                        country_id = self.env['res.country'].search(['|', ('name', '=', obj['description']['content']),
                                                                     ('code', '=', obj['isoCode'])], limit=1)
                        vals.update({'country_id': country_id and country_id[0].id or False})

                    elif obj.get('name') and search_req['type'] == 'city':
                        vals = {
                            'name': obj.get('name').get('content'),
                            'code': obj['code'],
                            'provider_id': provider_id[0].id,
                        }
                        city_id = self.env['res.country.city'].search([('name', '=', obj['name']['content'])], limit=1)
                        vals.update({'city_id': city_id and city_id[0].id or False})

                    elif obj.get('name') and search_req['type'] == 'hotel':
                        city_id = self.env['res.country.city'].search([('name', 'ilike', obj['city']['content'])], limit=1)
                        value = {
                            'name': obj['name']['content'],
                            'street': obj.get('address') and obj['address']['content'],
                            'description': obj.get('description') and obj['description'].get('content') or '',
                            'email': obj.get('email'),
                            'images': [(6, 0, self.rec_to_images(obj.get('images')))],
                            'phone': obj.get('phones') and obj.get('phones')[0].get('phoneNumber') + '(' + obj.get('phones')[0].get('phoneType') + ')' or '',
                            'phone_2': obj.get('phones') and len(obj['phones']) > 1 and obj.get('phones')[1].get('phoneNumber') + '(' + obj.get('phones')[1].get('phoneType') + ')' or '',
                            'phone_3': obj.get('phones') and len(obj['phones']) > 2 and obj.get('phones')[2].get('phoneNumber') + '(' + obj.get('phones')[2].get('phoneType') + ')' or '',
                            'zip': obj.get('postalCode'),
                            'website': obj.get('web'),
                            'lat': obj.get('coordinates') and str(obj.get('coordinates').get('latitude')),
                            'long': obj.get('coordinates') and str(obj.get('coordinates').get('longitude')),
                            # 'rating': obj.get('categoryCode') and int(obj.get('categoryCode')[0]),
                            'street2': obj['city']['content'],
                            'hotel_partner_city_id': city_id and city_id[0].id or False
                        }
                        hotel_id = self.env['tt.hotel'].create(value)
                        vals = {
                            'name': obj.get('name').get('content'),
                            'hotel_id': hotel_id.id,
                            'code': obj.get('code'),
                            'provider_id': provider_id[0].id,
                        }
                    if vals:
                        self.env['provider.code'].create(vals)
                        self.env.cr.commit()
        return True

    # Ambil record hotel dari prod. quantum
    # digunakan untuk homas
    # source data dari csv yg berisi city2x ne
    # Tembak ke Dev. side
    def get_record_by_api2a(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        # provider_id = self.env['res.partner'].search(
        #     [('is_master_vendor', '=', True), ('provider_code', '=', 'quantum')], limit=1)
        self.file_log_write('###### Quantum Render Start ######')
        with open('/var/log/cache_hotel/quantum/master/city_code.csv', 'r') as f:
            city_ids = csv.reader(f, delimiter=';')
            for idx, rec in enumerate(city_ids):
                if idx == 0:
                    continue
                search_req = {
                    'provider': 'quantum',
                    'type': 'city',
                    'limit': '0',
                    'offset': '0',
                    'codes': rec[1] + '~' + rec[0],
                }

                res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                if res['error_code'] != 0:
                    raise ('Error')
                else:
                    hotel_fmt_objs = []
                    for obj in res.get('response'):
                        if obj.get('code'):
                            hotel_fmt_objs.append({
                                'name': obj.get('basicinfo') and obj.get('basicinfo').get('name') or '',
                                'street': obj.get('addressinfo') and obj['addressinfo'].get('address1') or '',
                                'description': obj.get('locationinfo') and 'Raildistance: ' +
                                               obj['locationinfo'].get('raildistance', ' ') + '; Airport Distance: ' +
                                               obj['locationinfo'].get('airportdistance', ' ') or '',
                                'email': obj.get('contactinfo') and obj.get('contactinfo').get('email') or '',
                                'images': obj.get('images') or [],
                                'facilities': obj.get('hotelfacilities') or obj.get('roomfacilities') or [],
                                'phone': obj.get('contactinfo') and obj.get('contactinfo').get(
                                    'telephonenumber1') or '',
                                'fax': obj.get('contactinfo') and obj.get('contactinfo').get('faxnumber') or '',
                                'zip': obj.get('addressinfo') and obj['addressinfo'].get('zipcode'),
                                'website': obj.get('web'),
                                'lat': obj.get('coordinates') and str(obj.get('coordinates').get('latitude')),
                                'long': obj.get('coordinates') and str(obj.get('coordinates').get('longitude')),
                                'rating': obj.get('categoryCode') and int(obj.get('categoryCode')[0]) or 0,
                                'street2': obj.get('addressinfo') and 'City: ' + obj['addressinfo'].get('city`', ' ') +
                                           '; State: ' + obj['addressinfo'].get('state', ' ')  +
                                           '; Country: ' + obj['addressinfo'].get('country', ' ')or '',
                                'city': obj.get('addressinfo') and obj['addressinfo'].get('city') or '',
                                'id': obj.get('code'),
                            })
                    if hotel_fmt_objs:
                        with open('/var/log/cache_hotel/quantum/' + rec[2].replace('/', ' ') + '.json', 'w+') as f:
                            self.file_log_write(str(idx) + '. Hotel found for ' + rec[2] + ': ' + str(len(hotel_fmt_objs)) )
                            f.write(json.dumps(hotel_fmt_objs))
                    else:
                        self.file_log_write(str(idx) + '. No Hotel Found for ' + rec[2])
        f.close()
        self.file_log_write('###### Quantum Render END ######')
        return True

    # Quantum
    # Source data dari csv yg berisi city2x ne
    # Tembak ke Live Production
    def get_record_by_api2b(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        with open('/var/log/cache_hotel/quantum/master/city_code.csv', 'r') as f:
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
                            with open('/var/log/cache_hotel/quantum/' + rec[2].replace('/', ' ') + '.json', 'r') as f2:
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
                            with open('/var/log/cache_hotel/quantum/' + rec[2].replace('/', ' ') + '.json', 'w+') as f:
                                self.file_log_write(
                                    str(idx) + '. Hotel found for ' + rec[2] + ': ' + str(len(hotel_fmt_objs)))
                                f.write(json.dumps(hotel_fmt_objs))
                            hotel_in_file = hotel_fmt_objs

                        self.file_log_write('Total hotel for ' + rec[2] + ': ' + str(len(hotel_in_file)))
                        with open('/var/log/cache_hotel/quantum/' + rec[2].replace('/', ' ') + '.json', 'w+') as f:
                            f.write(json.dumps(hotel_in_file))

                    else:
                        self.file_log_write(str(idx) + '. No Hotel Found for ' + rec[2])
        f.close()
        return True

    # Quantum
    # Dari CSV Adrian
    def get_record_by_api2_2(self):
        hotel_fmt_list = {}
        with open('/var/log/cache_hotel/quantum_pool/master/QRHotelInfoDerby20190613.csv', 'r') as f:
            hotel_ids = csv.reader(f, delimiter=';')
            for obj in hotel_ids:
                # Formatting Hotel
                hotel_fmt_obj = {
                    'name': obj[2],
                    'street': obj[3],
                    'description': 'Rail:' + obj[16] + ' Distance: ' + obj[17] or '' if obj[16] else '',
                    'email': obj[13],
                    'images': [],
                    'facilities': [],
                    'phone': obj[11],
                    'fax': obj[12],
                    'zip': obj[10],
                    'website': '',
                    'lat': obj[25],
                    'long': obj[26],
                    'rating': obj[23] and obj[23][0] or '',
                    'street2': 'City: ' + obj[9] + '; Country: ' + obj[6] or '',
                    'city': obj[9].capitalize(),
                    'id': obj[1],
                }
                if not hotel_fmt_list.get(obj[9].capitalize()):
                    hotel_fmt_list[obj[9].capitalize()] = []
                # Add Hotel ke Dict
                hotel_fmt_list[obj[9].capitalize()].append(hotel_fmt_obj)
        f.close()
        need_to_add_list = [['No', 'Name', 'Hotel QTY']]
        self.file_log_write('###### Render Start ######')
        # Untuk setiap Key Loop
        for idx, city in enumerate(hotel_fmt_list.keys()):
            self.file_log_write("Write File " + city + " found : " + str(len(hotel_fmt_list[city])) + ' Hotel(s)')
            need_to_add_list.append([idx + 1, city, len(hotel_fmt_list[city]) ])
            filename = "/var/log/cache_hotel/quantum_pool/" + city.split('/')[0] + ".json"
            file = open(filename, 'w')
            file.write(json.dumps(hotel_fmt_list[city]))
            file.close()
        self.file_log_write('###### Render END ######')
        with open('/var/log/cache_hotel/quantum_pool/master/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    # Miki Travel
    # Get City -> Get Hotel -> **Simpan di DB**
    def get_record_by_api3(self):
        api_context = {
            'co_uid': self.env.user.id
        }

        search_req = {
            'provider': 'miki',
            'type': 'city',
            'limit': '0',
            'offset': '0',
            'codes': False,
        }

        res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        if res['error_code'] != 0:
            raise ('Error')
        else:
            for obj in res.get('response'):
                if obj.get('code'):
                    rec = self.env['res.city'].find_city_by_name(obj['addressinfo'].get('city', ''))
                    city_id = rec.city_id
                    value = {
                        'name': obj.get('basicinfo') and obj.get('basicinfo').get('name') or '',
                        'street': obj.get('addressinfo') and obj['addressinfo'].get('address1') or '',
                        'description': obj.get('locationinfo') and 'Raildistance: ' +
                                       obj['locationinfo'].get('raildistance', ' ') + '; Airport Distance: ' +
                                       obj['locationinfo'].get('airportdistance', ' ') or '',
                        'email': obj.get('contactinfo') and obj.get('contactinfo').get('email') or '',
                        'images': [(6, 0, self.rec_to_images(obj.get('images')))],
                        'phone': obj.get('contactinfo') and obj.get('contactinfo').get(
                            'telephonenumber1') or '',
                        'phone_2': '',
                        'phone_3': '',
                        'fax': obj.get('contactinfo') and obj.get('contactinfo').get('faxnumber') or '',
                        'zip': obj.get('addressinfo') and obj['addressinfo'].get('zipcode'),
                        'website': obj.get('web'),
                        'lat': obj.get('coordinates') and str(obj.get('coordinates').get('latitude')),
                        'long': obj.get('coordinates') and str(obj.get('coordinates').get('longitude')),
                        # 'rating': obj.get('categoryCode') and int(obj.get('categoryCode')[0]),
                        'street2': obj.get('addressinfo') and 'City: ' + obj['addressinfo'].get('city`', ' ') +
                                   '; State: ' + obj['addressinfo'].get('state', ' ') or '',
                        'hotel_partner_city_id': city_id and city_id[0].id or False
                    }
                    hotel_id = self.env['tt.hotel'].create(value)
                    self.env['provider.code'].create({
                        'name': hotel_id.name,
                        'hotel_id': hotel_id.id,
                        'code': obj.get('code'),
                        'provider_id': self.env['tt.provider'].search([('code', '=', 'miki')], limit=1).id,
                    })
                    self.env.cr.commit()

        return True

    # Miki Travel
    # Get Data dari XML read ambil dari FTP -> **Write di cache**
    # URL: ftp://ftp.mikinet.co.uk -> USER PASS ambil di Document vendor
    def get_record_by_api3a(self):
        file_ids = glob.glob("/var/log/cache_hotel/miki_api/master/*.xml")
        file_ids.sort()
        city_ids = {}
        try:
            for file_name in file_ids:
                _logger.info("Read " + file_name)
                try:
                    file = open(file_name, 'r')
                    hotel_list = file.read()
                    file.close()
                except:
                    continue
                for hotel in xmltodict.parse(hotel_list)['productInfoResponse']['productInfo']['product']:
                    # if hotel['productDescription']['productName'].title() == 'Achat Comfort':
                    #     pass
                    imgs = hotel['hotelProductInfo'].get('images') and hotel['hotelProductInfo']['images']['image'] or []
                    hotel_fmt = {
                        'id': hotel['productCode']['#text'],
                        'name': hotel['productDescription']['productName'].title(),
                        'description': hotel['productDescription']['productDetailText'],
                        'street': hotel['hotelProductInfo']['contactInfo']['address'].get('street1'),
                        'street2': hotel['hotelProductInfo']['contactInfo']['address'].get('street2','') + '; Country: ' + hotel['hotelProductInfo']['contactInfo']['address'].get('country') or '',
                        'city': hotel['hotelProductInfo']['contactInfo']['address'].get('city', '').title(),
                        'email': '',
                        'images': imgs and [{'name': img['@imageCaption'], 'url': img['@imageURL']} for img in isinstance(imgs, list) and imgs or [imgs]] or [],
                        'facilities': [key for (key, value) in hotel['hotelProductInfo']['hotelFacilities'].items() if value == 'true'] + [key for (key, value) in hotel['hotelProductInfo']['hotelRoomFacilities'].items() if value == 'true'],
                        'phone': hotel['hotelProductInfo']['contactInfo'].get('telephoneNumber'),
                        'fax': hotel['hotelProductInfo']['contactInfo'].get('faxNumber'),
                        'zip': hotel['hotelProductInfo']['contactInfo']['address'].get('street3'),
                        'website': '',
                        'lat': '',
                        'long': '',
                        'rating': hotel['hotelProductInfo']['hotelInfo'].get('starRating') or '',
                    }

                    _logger.info("Adding Hotel:" + hotel_fmt['name'] + ' in City: ' + hotel_fmt['city'])
                    if not city_ids.get(hotel_fmt['city']):
                        city_ids[hotel_fmt['city']] = []
                    city_ids[hotel_fmt['city']].append(hotel_fmt)
        except Exception as e:
            _logger.info("Error in " + file_name[36:] + ' Name:' + hotel_fmt['name'] +' Error: ' + str(e) + '.')
        # Write per City
        need_to_add = [['Name', 'Hotel Qty']]
        for city_rec in city_ids.keys():
            city_rec = city_rec.replace('/', '')
            _logger.info("Write File " + city_rec + ": " + str(len(city_ids[city_rec])))
            filename = "/var/log/cache_hotel/miki_api/" + city_rec + ".json"
            file = open(filename, 'w')
            file.write(json.dumps(city_ids[city_rec]))
            file.close()
            need_to_add.append([city_rec, len(city_ids[city_rec])])
        with open('/var/log/cache_hotel/miki_api/result/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add)
        csvFile.close()
        return True

    # Miki Travel Pool Data tgl 20190703
    def get_record_by_file3a(self):
        with open('/var/log/cache_hotel/miki_pool/master/20190703_en.csv', 'r') as f:
            hotel_ids = csv.reader(f)

            hotel_fmt_list = {}
            index = False
            for hotel in hotel_ids:
                if not index:
                    index = hotel
                    continue
                # _logger.info("Processing (" + hotel[5] + ").")
                hotel_fmt = {
                    'id': hotel[0],
                    'name': hotel[5],
                    'street': hotel[6],
                    'street2': hotel[7] or '',
                    'street3': hotel[8] or '',
                    'description': 'Supplier Code: ' + str(hotel[4]),
                    'email': '',
                    'images': [],
                    'facilities': [],
                    'phone': hotel[11],
                    'fax': hotel[12],
                    'zip': '',
                    'website': '',
                    'lat': hotel[9],
                    'long': hotel[10],
                    'rating': 0,
                    'hotel_type': '',
                    'city': hotel[2],
                }
                if not hotel_fmt_list.get(hotel_fmt['city']):
                    hotel_fmt_list[hotel_fmt['city']] = []
                hotel_fmt_list[hotel_fmt['city']].append(hotel_fmt)

            need_to_add = [['Name', 'Hotel Qty']]
            for city in hotel_fmt_list.keys():
                _logger.info("Write File " + city + ": " + str(len(hotel_fmt_list[city])))
                filename = "/var/log/cache_hotel/miki_pool/" + city + ".json"
                file = open(filename, 'w')
                file.write(json.dumps(hotel_fmt_list[city]))
                file.close()

                need_to_add.append([city, len(hotel_fmt_list[city])])
        f.close()

        with open('/var/log/cache_hotel/miki_pool/master/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add)
        csvFile.close()

    # C-Trip Travel
    def get_record_by_api4(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        repeat = True

        search_req = {
            'provider': 'ctrip',
            'type': 'city',
            'limit': '20',
            'offset': '2',
            'codes': 2,
        }
        provider_id = self.env['res.partner'].search([('provider_code', '=', 'ctrip')], limit=1)
        for prov_city in self.env['provider.code'].search([('city_id', '!=', False), ('provider_id', '=', provider_id[0].id)]):
            search_req['codes'] = prov_city.code
            while repeat:
                res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                if res['error_code'] != 0:
                    repeat = False
                    raise ('Error')
                else:
                    for obj in res.get('response')[1]:
                        if obj.get('HotelStaticInfo'):
                            obj = obj['HotelStaticInfo']
                            city_id = prov_city.city_id.id
                            geo_info = obj.get('GeoInfo') and obj['GeoInfo'].get('Coordinates') and obj['GeoInfo']['Coordinates'] or False
                            if geo_info:
                                geo_info = filter(lambda x: x['Provider'] == 'Google', geo_info)[0] or geo_info[0]
                            value = {
                                'name': obj.get('HotelName') or '',
                                'rating': obj.get('StarRating') or 1,
                                'street': obj.get('GeoInfo') and obj['GeoInfo'].get('Address') or '',
                                'street2': obj.get('GeoInfo') and str(obj['GeoInfo']) or '',
                                'description': obj.get('Descriptions') and obj['Descriptions'][0]['Text'] or '',
                                'email': obj.get('contactinfo') and obj.get('contactinfo').get('email') or '',
                                'images': [(6, 0, self.rec_to_images2(obj.get('Pictures')))],
                                'phone': obj.get('ContactInfo') and obj.get('ContactInfo').get('Telephone') or '',
                                'phone_2': '',
                                'phone_3': res.get('response')[0],
                                'fax': obj.get('ContactInfo') and obj.get('ContactInfo').get('Fax') or '',
                                'zip': obj.get('GeoInfo') and obj['GeoInfo'].get('PostalCode'),
                                'website': obj.get('web'),
                                'lat': geo_info.get('LAT'),
                                'long': geo_info.get('LNG'),
                                'hotel_partner_city_id': city_id,
                                'tac': obj.get('ImportantNotices') and self.rec_to_tac(obj.get('ImportantNotices')) or '',
                            }
                            hotel_id = self.env['tt.hotel'].create(value)
                            self.env['provider.code'].create({
                                'name': hotel_id.name,
                                'hotel_id': hotel_id.id,
                                'code': obj.get('HotelID'),
                                'provider_id': provider_id[0].id,
                            })
                            self.env.cr.commit()
                            hotel_id.get_provider_name()
                    if res.get('response')[0] == search_req['offset']:
                        repeat = False
                    else:
                        search_req['offset'] = str(int(search_req['offset']) + 1)
            return True

    # Itank Travel
    # Ambil List Country & City, List Hotel untuk setiap city
    def get_record_by_api5(self):
        city_ids = []
        provider_id = self.env['res.partner'].search(
            [('is_master_vendor', '=', True), ('provider_code', '=', 'itank')], limit=1)
        api_context = {
            'co_uid': self.env.user.id
        }
        search_req = {
            'provider': 'itank',
            'type': 'country',
            'limit': '20',
            'offset': '1',
            'codes': '',
        }
        res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        #filter(lambda x: x['name'] in ['Indonesia' , 'Malaysia', 'Thailand', 'Singapore', 'China', 'Myanmar'], res['response'])
        # for country in filter(lambda x: x['name'] in ['Indonesia',], res['response']):
        for country in res['response']:
            vals = {
                'name': country['name'],
                'code': country['code'],
                'provider_id': provider_id[0].id,
            }
            country_id = self.env['res.country'].search(['|', ('name', '=', country['name']),
                                                         ('code', '=', country['code'])], limit=1)
            if country_id:
                vals.update({'country_id': country_id and country_id[0].id or False})
            self.env['provider.code'].create(vals)
            self.env.cr.commit()

            for city in country['cities']:
                vals = {
                    'code': city['code'],
                    'name': city['name'],
                    'provider_id': provider_id[0].id,
                }
                city_id = self.env['res.country.city'].search([('name', 'ilike', city['name'])], limit=1)
                if city_id:
                    vals.update({'city_id': city_id and city_id[0].id or False})
                    city_ids.append({
                        'code': city['code'],
                        'city_id': city_id[0].id,
                        'country_code': country['code']
                    })
                self.env['provider.code'].create(vals)
                self.env.cr.commit()

        for rec in city_ids:
            if rec['code'] and rec['country_code']:
                search_req = {
                    'provider': 'itank',
                    'type': 'hotel',
                    'limit': '20',
                    'offset': '1',
                    'codes': str(rec['code']) + '~' + str(rec['country_code']),
                }
                res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                for hotel_rec in res['response'][:10]:
                    # temp_data = self.env['provider.code'].search(
                    #     [('provider_id', '=', provider_id[0].id), ('code', '=', hotel_rec['code']), ('hotel_id', '!=', False)])
                    # # Rec already exist
                    # if temp_data:
                    #     temp_data[0].hotel_id.update({
                    #         'star': hotel_rec['star'],
                    #         'email': hotel_rec['email'],
                    #         'phone': hotel_rec['phone'],
                    #         'fax': hotel_rec['fax'],
                    #         'url': hotel_rec['url'],
                    #         'address': hotel_rec['address'],
                    #         'lat': hotel_rec['lat'],
                    #         'long': hotel_rec['long'],
                    #         'zip': hotel_rec['zip'],
                    #         'hotel_desc': hotel_rec['hotel_desc'],
                    #         'hotel_image': hotel_rec['hotel_image']
                    #     })
                    # else:
                    if hotel_rec: # Remark Waktu ada pengencekan already exist record
                        # Create Hotel
                        hotel_id = self.env['tt.hotel'].sudo().create({
                            'name': hotel_rec['name'],
                            'rating': hotel_rec['star'],
                            'email': hotel_rec['email'],
                            'phone': hotel_rec['phone'],
                            'fax': hotel_rec['fax'],
                            'website': hotel_rec['url'],
                            'address': hotel_rec['address'],
                            'hotel_partner_city_id': rec['city_id'],
                            'lat': hotel_rec['lat'],
                            'long': hotel_rec['long'],
                            'zip': hotel_rec['zip'],
                            'description': hotel_rec['hotel_desc'],
                        })
                        if hotel_rec['hotel_image']:
                            continue
                        # Create Provider Code
                        self.env['provider.code'].sudo().create({
                            'code': hotel_rec['code'],
                            'provider_id': provider_id[0].id,
                            'hotel_id': hotel_id.id
                        })
                        self.env.cr.commit()
        return True

    def resp_itank_to_odoo(self, hotel_rec):
        self.update({
            'name': hotel_rec.get('name'),
            'rating': hotel_rec.get('star') and int(hotel_rec['star']) or '',
            'email': hotel_rec.get('email'),
            'phone': hotel_rec.get('phone'),
            'fax': hotel_rec.get('fax'),
            'website': hotel_rec.get('url'),
            'street': hotel_rec.get('address'),
            'lat': hotel_rec.get('lat'),
            'long': hotel_rec.get('long'),
            'zip': hotel_rec.get('zip'),
            'description': ''.join(rec + '\n' for rec in hotel_rec.get('hotel_desc')),
        })
        for rec in hotel_rec['hotel_img']:
            self.file_log_write("Image for %s" % rec['title'])
            self.env['product.image'].create({
                'hotel_id': self.id,
                'name': rec['title'],
                'image_url_complete': rec['url'],
            })
        self.env.cr.commit()

    def resp_vendor_to_homas(self, hotel_rec, city_name):
        return {
            'id': hotel_rec.get('code'),
            'name': hotel_rec.get('name'),
            'rating': hotel_rec.get('star') and int(hotel_rec['star']) or '',
            'email': hotel_rec.get('email'),
            'phone': hotel_rec.get('phone'),
            'fax': hotel_rec.get('fax'),
            'website': hotel_rec.get('url'),
            'city': hotel_rec.get('city', city_name),
            'street': hotel_rec.get('address'),
            'lat': hotel_rec.get('lat'),
            'long': hotel_rec.get('long'),
            'zip': hotel_rec.get('zip'),
            'description': ''.join(rec + '\n' for rec in hotel_rec.get('hotel_desc',[])),
            'images': [rec['url'] for rec in hotel_rec.get('hotel_img',[])],
            'facilities': [rec['name'] for rec in hotel_rec.get('facilities',[])],
        }

    # Itank Travel
    def get_record_detail_by_api5(self, city_code, hotel_ids):
        # provider_id = 2282
        provider_id = self.env['res.partner'].search(
            [('is_master_vendor', '=', True), ('provider_code', '=', 'itank')], limit=1)[0].id
        api_context = {
            'co_uid': self.env.user.id
        }

        if not city_code:
            city_code = self.hotel_partner_city_id.provider_city_ids.filtered(lambda x: x.provider_id.id == provider_id)[0].code
        country_code = self.hotel_partner_city_id.country_id.provider_city_ids.filtered(lambda x: x.provider_id.id == provider_id)[0].code
        # country_code = 'ID'
        hotel_code = self.provider_hotel_ids.filtered(lambda x: x.provider_id.id == provider_id)[0].code
        search_req = {
            'provider': 'itank',
            'type': 'hoteldetail',
            'limit': '20',
            'offset': '1',
            'codes': str(city_code) + '~' + str(country_code) + '~' + str(hotel_code),
        }
        res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        if not res['response']:
            self.file_log_write("No hotel Found for %s." % self.name)
            return {'id': self.hotel_partner_city_id.id, 'code': city_code, 'name': self.hotel_partner_city_id.name, 'hotel_ids': hotel_ids}

        for hotel_rec in res['response']:
            # self.resp_itank_to_odoo(hotel_rec)
            hotel_ids.append(self.resp_vendor_to_homas(hotel_rec, self.hotel_partner_city_id.name))
        return {'id': self.hotel_partner_city_id.id, 'code': city_code, 'name': self.hotel_partner_city_id.name,'hotel_ids': hotel_ids}

    def file_log_write(self, str, log_type='info'):
        try:
            with open('/var/log/cache_hotel/itank/logger.txt', 'a+') as file_log:
                file_log.write('\n' + str)
            file_log.close()
            if log_type == 'info':
                _logger.info(str)
            else:
                _logger.error(str)
        except:
            if log_type == 'info':
                _logger.info(str)
            else:
                _logger.error(str)

    def get_record_by_api5a(self):
        last_city = {'id': False}
        hotel_ids = []
        last_city_name = ''
        self.file_log_write('###### Render Start ######')
        for idx, rec in enumerate(self.env['tt.hotel'].search([('id', '>=', self.id)])):
            try:
                if last_city['id'] == rec.hotel_partner_city_id.id:
                    city_code = last_city['code']
                else:
                    city_code = False
                    if hotel_ids:
                        with open('/var/log/cache_hotel/itank/' + last_city_name + '.json', 'w+') as f:
                            self.file_log_write("Write " + str(len(hotel_ids)) + " Hotel(s) for " + last_city_name + " in: /var/log/cache_hotel/itank/" + last_city_name + ".json")
                            f.write(json.dumps(hotel_ids))

                    hotel_ids = []
                self.file_log_write("Processing %s. %s" % (idx+1, rec.name))
                last_city = rec.get_record_detail_by_api5(city_code, hotel_ids)
                hotel_ids = last_city.pop('hotel_ids') or hotel_ids
                last_city_name = last_city.pop('name')
            except:
                self.file_log_write(("Error acquirer for Hotel %s: %s" % (idx+1, rec.name)), 'error')
        self.file_log_write('###### Render END ######')

    def get_record_by_api5b(self):
        list_hotel = self.env['tt.hotel'].search([('id', '>=', self.id)])
        for rec in list_hotel:
            try:
                # 1. Find hotel dengan city yg sama
                # 2. Loop untuk proses
                hotel_fmt_objs = [rec.resp_vendor_to_homas(rec2, rec2.hotel_partner_city_id.name) for rec2 in filter(lambda x:x.hotel_partner_city_id.id == rec.hotel_partner_city_id.id, list_hotel)]
                # 3. Simpan ke File
                if hotel_fmt_objs:
                    with open('/var/log/cache_hotel/itank/' + rec.hotel_partner_city_id.name + '.json', 'w+') as f:
                        f.write(json.dumps(hotel_fmt_objs))
                # 4. Remove hotel yg telah di proses
                hotel_fmt_objs = [a['name'] for a in hotel_fmt_objs]
            except:
                _logger.error("Error acquirer for City: %s" % rec.hotel_partner_city_id.name)

    # Itank Remove
    def remove_itank(self):
        provider_id = self.env['res.partner'].search(
            [('is_master_vendor', '=', True), ('provider_code', '=', 'itank')], limit=1)
        recs = self.env['provider.code'].search([('provider_id', '=', provider_id[0].id)])
        for rec in recs:
            rec.sudo().unlink()

    # Web Beds / Fitruums
    # Ambil dari API lalu simpan sebagai cache
    def get_record_by_api6b(self):
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
        return API_CN_HOTEL.get_record_by_api(search_req, api_context)

    # Ambil Hotel dari API lalu simpan sebagai cache
    def get_record_by_api6b_2(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        with open('/var/log/cache_hotel/webbeds_pool/dest_list.csv', 'r') as f:
            city_ids = csv.reader(f)
            a = 0
            base_url = 'http://www.sunhotels.net/Sunhotels.net/HotelInfo/hotelImage.aspx'

            for rec in city_ids:
                if a < 3171: #15967
                    a += 1
                    continue
                try:
                    _logger.info("Processing (" + rec[2] + ").")
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
                        'name': obj['name'].encode("utf-8"),
                        'street': obj.get('hotel.addr.1') and obj['hotel.addr.1'].encode("utf-8") or '',
                        'street2': obj.get('hotel.addr.2') and obj['hotel.addr.2'].encode("utf-8") or '',
                        'street3': obj.get('hotel.address') and obj['hotel.address'].encode("utf-8") or '',
                        'description': obj.get('descriptions') and
                            obj['descriptions'].get('hotel_information').encode("utf-8") or '',
                        'email': '',
                        'images': obj['images'] and [base_url + recs['fullSizeImage']['@url'] if recs.get('fullSizeImage') else recs['smallImage']['@url'] for recs in
                                                     isinstance(obj['images']['image'], list) and obj['images'][
                                                         'image'] or [obj['images']['image']]] or [],
                        'facilities': obj['features'] and [{'facility_id': '', 'url': '','facility_name': recs['@name'], 'description': 'VendorID:' + str(recs['@id'])} for recs in
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
                        'city': obj.get('destination') or '',
                    } for obj in res['response'][1]]

                    filename = "/var/log/cache_hotel/webbeds_pool/" + rec[2] + ".json"
                    file = open(filename, 'w')
                    file.write(json.dumps(hotel_fmt_list))
                    file.close()
                    _logger.info("Done City: " + rec[2] + ' get: ' + str(len(hotel_fmt_list)) + ' Hotel(s)')
                except Exception as e:
                    _logger.info("Error " + rec[2] + ': ' + str(e) + '.')
                    continue

    # WebBeds: Tools untuk hitung jumlah hotel per city dan kelengkapan data nya
    def get_record_by_api6b_3(self):
        with open('/var/log/cache_hotel/webbeds_pool/dest_list.csv', 'r') as f:
            city_ids = csv.reader(f)
            a = 0
            need_to_add_list = [['No', 'Name', 'Hotel QTY', 'Hv Images', 'Hv Facilities', 'Hv Rating', 'Img Ratio',
                                 'Fac Ratio', 'Rating Ratio']]
            for rec in city_ids:
                if a == 0:
                    a += 1
                    continue
                temp_filename = "/var/log/cache_hotel/webbeds_pool/" + rec[2] + ".json"
                _logger.info("Opening file (" + temp_filename + ").")
                try:
                    with open(temp_filename, 'r') as f2:
                        try:
                            a = f2.read()
                            record = json.loads(a)
                            hotel_qty = len(record)
                            hotel_img = hotel_fac = hotel_rating = 0
                            for recs in record:
                                hotel_img += recs['images'] and 1 or 0
                                hotel_fac += recs['facilities'] and 1 or 0
                                hotel_rating += recs['rating'] and 1 or 0
                            need_to_add_list.append([a, rec[2].encode("utf-8"), hotel_qty,
                                                     hotel_img, hotel_fac, hotel_rating,
                                                     float(hotel_img / hotel_qty),
                                                     float(hotel_fac / hotel_qty), float(hotel_rating / hotel_qty)])
                        except:
                            need_to_add_list.append([a, rec[2].encode("utf-8"), 'error',
                                                     0, 0, 0, 0, 0, 0])
                except:
                    need_to_add_list.append([a, rec[2].encode("utf-8"), 'Not Found',
                                             0, 0, 0, 0, 0, 0])
                f2.close()

            with open('/var/log/cache_hotel/webbeds_pool/result_data.csv', 'w') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerows(need_to_add_list)
            csvFile.close()

    # WebBeds: Cache webbeds diambil tiap 2 minggu sekali
    def get_record_by_csv_6(self):
        with open('/var/log/cache_hotel/webbeds_excel_pool/master_data/hotel_static_data.csv', 'r') as f:
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
                    last_name = last_name.replace('/','-')
                    filename = "/var/log/cache_hotel/webbeds_excel_pool/" + last_name + ".json"
                    file = open(filename, 'w')
                    file.write(json.dumps(hotel_fmt_list))
                    file.close()
                    _logger.info("Done City: " + last_name + ' get: ' + str(len(hotel_fmt_list)) + ' Hotel(s)')
                    last_name = rec[5]
                    hotel_fmt_list = []
                hotel_fmt_list.append(hotel_fmt)

        f.close()
        return True

    # DIDA
    # Ambil dari Pool lalu simpan sebagai cache
    # Get Info Country, Meal Type, Room Type, Prop. Type
    def get_record_by_api7a(self):
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
                        need_to_add_list.append([gw_rec['ID'], gw_rec['Name'] ])
                else:
                    # BedTypes, Breakfasts, PropertyCategorys, MealTypes
                    for gw_rec in a[rec+'s']:
                        need_to_add_list.append([gw_rec['ID'], gw_rec.get('Name') or gw_rec.get('Description_EN') ])

                with open('/var/log/cache_hotel/dida_pool/master/' + rec + '.csv', 'w') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerows(need_to_add_list)
                csvFile.close()
            except:
                _logger.info('Error While rendering Get' + rec + 'List')
                continue
        return True

    # Get Info City
    def get_record_by_api7b(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        # Read List
        with open('/var/log/cache_hotel/dida_pool/master/Country.csv', 'r') as f:
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
                                                 gw_rec['CountryCode'] ])
                except:
                    _logger.info("No City for: " + rec[1] + ".")
                    continue
        f.close()
        with open('/var/log/cache_hotel/dida_pool/master/City.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    # Get Hotel Static
    def get_record_by_api7c(self):
        # api_context = {
        #     'co_uid': self.env.user.id
        # }
        # search_req = {
        #     'provider': 'dida',
        #     'type': 'GetHotelStaticInformation',
        #     'limit': '',
        #     'offset': '',
        #     'codes': rec,
        # }
        # url = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        # URL open
        with open('/var/log/cache_hotel/dida_pool/master/AvailHotelSummary_V0.csv', 'r') as f:
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
                    'street3': 'State: ' + hotel[8] or '' + ', Country: ' + hotel[10],
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
                }
                if not hotel_fmt_list.get(hotel_fmt['city']):
                    hotel_fmt_list[hotel_fmt['city']] = []
                hotel_fmt_list[hotel_fmt['city']].append(hotel_fmt)

            for city in hotel_fmt_list.keys():
                txt_city = city.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')', '')
                _logger.info("Write File " + txt_city)
                filename = "/var/log/cache_hotel/dida_pool/" + txt_city + ".json"
                file = open(filename, 'w')
                file.write(json.dumps(hotel_fmt_list[city]))
                file.close()
        f.close()

    # MGHoliday
    def get_record_by_folder8(self):
            need_to_add_list = [['No', 'City', 'Country', 'Hotel qty']]
            # Find all xls file in selected directory
            path = '/var/log/cache_hotel/mg_pool/ori'
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
                    a = 0
                    body = {}
                    # dikasih len header supaya header tidak ikut di render
                    for rec in tree.xpath('//td')[len(header):]:
                        body[header[a]] = rec.text if rec.text != "" else ''
                        # Reset pointer setelah header habis
                        if a == len(header) - 1:
                            # Prepare dict to format cache
                            if not hotel_list.get(body['CityName']):
                                hotel_list[body['CityName']] = []
                            hotel_list[body['CityName']].append({
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
                            })
                            body = {}
                            a = 0
                        else:
                            a += 1
                f.close()
                for city in hotel_list.keys():
                    _logger.info("City: " + city + ' Get:' + str(len(hotel_list[city])) + 'Hotel(s)')
                    filename = "/var/log/cache_hotel/mg_pool/" + city.strip().split('/')[0] + ".json"
                    file = open(filename, 'w')
                    file.write(json.dumps(hotel_list[city]))
                    file.close()

                    need_to_add_list.append([1, hotel_list[city].encode("utf-8"),
                                             country_file.split('/')[-1].split('_')[2].encode("utf-8"),
                                             len(hotel_list[city])])

            with open('/var/log/cache_hotel/mg_pool/ori/Result.csv', 'w') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerows(need_to_add_list)
            csvFile.close()

    # TBO Holidays
    # Get Country, City
    def get_record_by_api9(self):
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

            _logger.info("Get City for Country: " + gw_rec['name'])
            search_req = {
                'provider': 'tbo',
                'type': 'city',
                'limit': '',
                'offset': '',
                'codes': gw_rec['code'],
            }
            try:
                city_resp = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                filename = '/var/log/cache_hotel/tbo/master/' + gw_rec['name'].lower() + '.txt'
                file = open(filename, 'w')
                file.write(json.dumps(city_resp['response'][1]))
                file.close()
            except:
                continue
        with open('/var/log/cache_hotel/tbo/master/country.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()
        return True

    # TBO Holidays
    # Get Hotel
    def get_record_by_api9a(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        i = 1
        need_to_add_list = [['No', 'City', 'Country', 'Hotel qty']]
        with open("/var/log/cache_hotel/tbo/master/country.csv", 'r') as file:
            file_content = csv.reader(file)
            for rec in file_content:
                # open file
                filename = '/var/log/cache_hotel/tbo/master/' + rec[1].lower() + '.txt'
                try:
                    file = open(filename, 'r')
                    country_file = json.loads(file.read())
                    file.close()
                except:
                    continue
                # loop per city ke fungsi get hotel giata
                for city in country_file:
                # for city in [{'code':'126632'}, {'code':'115936'}, {'code':'131408'}]:
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
                        hotel_fmt = hotel_objs['response'][1]
                        length = len(hotel_fmt)
                    except:
                        length = 0
                    # _logger.info("Get "+str(length)+" Hotel(s) for City: " + city + ', ' + rec[1])
                    # need_to_add_list.append([i, city, rec[1], length])
                    # filename = "/var/log/cache_hotel/tbo/" + city + ".json"

                    _logger.info("Get "+str(length)+" Hotel(s) for City: " + city['name'] + ', ' + rec[1])
                    need_to_add_list.append([i, city['name'].split(',')[0], rec[1], length])
                    filename = "/var/log/cache_hotel/tbo/" + city['name'].split(',')[0].replace('/', '-') + ".json"

                    i += 1
                    # Create Record Hotel per City
                    file = open(filename, 'w')
                    file.write(json.dumps(hotel_fmt))
                    file.close()
        file.close()

        with open('/var/log/cache_hotel/tbo/master/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()
        return True

    # OYO TMC
    # Get All Hotel (by hotel Code/ 'IN')
    def get_record_by_api10(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        i = 75
        limit = 100
        all_obj = (i*limit)+1
        while i*limit < all_obj:
            search_req = {
                'provider': 'oyo',
                'type': 'hotel',
                'limit': limit,
                'offset': i*limit,
                'codes': 'IN', #Country Code
            }
            hotel_fmt = []
            _logger.info("Get offset " + str(i*limit) + " Hotel(s) ")
            try:
                hotel_objs = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                all_obj = hotel_objs['response'][0]
                hotel_fmt = hotel_objs['response'][1]
            except:
                all_obj = 0

            filename = "/var/log/cache_hotel/oyo/master/" + 'IN' + '_' + str(i) + ".json"
            i += 1
            # Create Record Hotel per City
            file = open(filename, 'w')
            file.write(json.dumps(hotel_fmt))
            file.close()
        return True

    # OYO TMC
    # Mapping Hotel
    def get_record_by_api10b(self):
        file_ids = glob.glob("/var/log/cache_hotel/oyo/master/*.json")
        # TODO pertimbangkan pengelompokan per country
        city_ids = {}
        for file in file_ids:
            _logger.info("Read " + file)
            try:
                file = open(file, 'r')
                hotel_list = json.loads(file.read())
                file.close()
            except:
                continue
            for rec in hotel_list:
                if not city_ids.get(rec['city']):
                    city_ids.update({
                        rec['city']: [],
                    })
                city_ids[ rec['city'] ].append(rec)

        i = 1
        need_to_add_list = [['No', 'City', 'Country', 'Hotel qty']]
        for city in city_ids:
            _logger.info("Creating " + str(i) + ": " + city + ' Found: ' + str(len(city_ids[city])) + ' Hotel(s)')
            filename = "/var/log/cache_hotel/oyo/" + city.replace('/', '-') + ".json"

            need_to_add_list.append([i, city, '', str(len(city_ids[city])) ])
            # Create Record Hotel per City
            file = open(filename, 'w')
            file.write(json.dumps(city_ids[city]))
            file.close()
            i += 1

        with open('/var/log/cache_hotel/oyo/master/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()
        return True

    # ====================== TOOLS =====================================================
    def masking_provider(self, provider):
        # Perlu dibuat gini karena cache data bisa berasal dari mana sja
        # EXAMPLE: mg_pool, miki_api, hotelspro_file, dida_pool dll
        provider = provider.split('_')[0]
        if provider in ['mg', 'mgholiday']:
            return 'A1'
        elif provider == 'hotelspro':
            return 'A2'
        elif provider == 'miki':
            return 'A3'
        elif provider == 'itank':
            return 'A4'
        elif provider == 'quantum':
            return 'A5'
        elif provider in ['webbeds', 'fitruums']:
            return 'A6'
        elif provider == 'hotelbeds':
            return 'A7'
        elif provider == 'dida':
            return 'A8'
        elif provider == 'tbo':
            return 'A9'
        elif provider == 'welcomebeds':
            return 'A10'
        elif provider == 'oyo':
            return 'A11'
        else:
            return provider

    def formating_homas(self, hotel, hotel_id, provider, city_id, city_name):
        new_hotel = {
                    'id': str(hotel_id),
                    'name': hotel.get('name') and hotel['name'].title(),
                    'rating': hotel.get('rating', 0),
                    'prices': [],
                    'description': hotel.get('description'),
                    'location': {
                        'city_id': city_id,
                        'address': hotel.get('address') or hotel.get('street'),
                        'city': hotel.get('city', city_name),
                        'state': hotel.get('state_id.name'),
                        'district': hotel.get('district_id'),
                        'kelurahan': hotel.get('kelurahan'),
                        'zipcode': hotel.get('zip')
                    },
                    'telephone': hotel.get('phone'),
                    'fax': hotel.get('fax'),
                    'ribbon': '',
                    'lat': hotel.get('lat'),
                    'long': hotel.get('long'),
                    'state': 'confirm',
                    'external_code': {self.masking_provider(provider): str(hotel.get('id',''))},
                    'near_by_facility': [],
                    'images': hotel.get('images') or hotel.get('image'),
                    'facilities': hotel.get('facilities'),
                }
        if not isinstance(new_hotel['rating'], int):
            try:
                new_hotel['rating'] = int(new_hotel['rating'][0])
            except:
                new_hotel['rating'] = 0

        fac_list = []
        for img in new_hotel.get('images') or []:
            if isinstance(img, str):
                new_img_url = 'http' in img and img or 'http://www.sunhotels.net/Sunhotels.net/HotelInfo/hotelImage.aspx' + img + '&full=1'
                fac_list.append({'name': '', 'url': new_img_url})
            else:
                # Digunakan hotel yg bisa dpet nama image nya
                # Sampai tgl 11-11-2019 yg kyak gini (miki_api) formate sdah bener jadi bisa langsung break
                # Lek misal formate beda mesti di format ulang
                fac_list = new_hotel['images']
                break
        new_hotel['images'] = fac_list

        for fac in new_hotel.get('facilities') or []:
            if isinstance(fac, dict):
                if not fac.get('facility_name'):
                    fac['facility_name'] = fac.pop('name')
                fac_name = fac['facility_name']
            else:
                fac_name = fac
                fac = {
                    'facility_name': fac,
                    'facility_id': False,
                }
            # fac_name = isinstance(fac, dict) and fac['facility_name'] or fac
            facility = self.env['tt.hotel.facility'].search([('name', '=ilike', fac_name)])
            fac['facility_id'] = facility and facility[0].id or False
        return new_hotel

    def formatting_hotel_name(self, hotel_name, city_name=False):
        # Comparing Hotel Tunjungan Surabaya dengan Tunjungan Hotel Surabaya
        # 1. Set to lower
        # 2. Split using " "
        fmt_hotel_name = hotel_name.lower()
        for param in ['-', '_', '+', ',', '.', ';']:
            fmt_hotel_name = fmt_hotel_name.replace(param, ' ')
        fmt_hotel_name = fmt_hotel_name.replace('@', 'at ')
        fmt_hotel_name = fmt_hotel_name.replace('   ', ' ')
        fmt_hotel_name = fmt_hotel_name.replace('  ', ' ')
        fmt_hotel_name = fmt_hotel_name.split(' ')
        # 3. Remove Selected String (Hotel, Motel, Apartement , dsb)
        # 4. Remove City Name
        ext_param = ['hotel', 'motel', 'villa', 'villas', 'apartment', 'and', '&', '&amp;']
        ext_param += city_name and city_name.lower().split(' ') or []

        # 5. Remove Ex/Formerly Name
        # Example: Hardys Hotel Singaraja (Formerly POP Hotel Hardys Singaraja); Neo Denpasar (formerly Neo Gatot Subroto Bali)
        # Example: Swiss-belhotel Lampung (ex The 7th Hotel & Convention Center); D'Best Hotel Bandung - Managed by Dafam Hotels
        # Example: Shakti Hotel Bandung ( ex MaxOneHotels at Soekarno Hatta Bandung); Aston Tropicana(Ex. Aston Tropicana hotel and Plaza)
        # Example: Holiday Inn Pasteur(ex.Aston Primera Pasteur); Aston Pasteur Hotel (Previous Harper Pasteur - Bandun)

        return [e for e in fmt_hotel_name if e not in ext_param]

    def advance_find_similar_name(self, hotel_name, city_name, cache_content):
        fmt_hotel_name = self.formatting_hotel_name(hotel_name, city_name)

        for rec in cache_content:
            if all(elem in " ".join(self.formatting_hotel_name(rec['name'])) for elem in fmt_hotel_name):
                return [rec,]
        return False

    # Get Record From HOMAS, pool, api langsung jadi file cache
    # By City
    def get_record_homas_all(self):
        # Read CSV CITY
        target_city_index = 0
        hotel_id = 0

        with open('/var/log/cache_hotel/res_country_city.csv', 'r') as f:
            self.file_log_write('=================================')
            self.file_log_write('== Cache Hotel for Homas START ==')
            self.file_log_write('=================================')
            # provider_list = ['hotelspro', 'miki', 'fitruums', 'itank', 'quantum', 'mgholiday',
            #                  'mg_pool', 'hotelspro_file', 'miki_pool', 'webbeds_pool',
            #                  'dida_pool', 'quantum_pool', 'tbo']
            provider_list = ['webbeds_pool']

            need_to_add_list = [['No', 'CityName'] + provider_list + ['Total']]
            new_to_add_list2 = [['Type', 'Name', 'Similar Name']]
            city_ids = csv.reader(f)
            for target_city in city_ids:
                if target_city_index == 0:
                    target_city_index += 1
                    continue
                cache_content = []
                try:
                    city_id = self.env.ref(target_city[0]).id
                except:
                    city_obj = self.env['res.country.city'].search([('name', '=', target_city[1])], limit=1)
                    city_id = city_obj and city_obj.id or False
                new_to_add_list = [target_city_index, target_city[1]]
                # Loop All provider
                self.file_log_write(str(target_city_index) + '. Start Render: ' + target_city[1])
                for provider in provider_list:
                    try:
                        # Loop untuk setiap city cari file yg nama nya sma dengan  city yg dimaksud
                        extention = '.json' if provider != 'hotelspro_file' else '.txt'
                        with open('/var/log/cache_hotel/' + provider + '/' + str(target_city[1]) + extention, 'r') as f2:
                            file = f2.read()
                            self.file_log_write('Provider ' + provider + ': ' + str(len(json.loads(file))))
                            new_to_add_list.append(len(json.loads(file)))
                            for hotel in json.loads(file):
                                hotel_id += 1
                                # rubah format ke odoo
                                hotel_fmt = self.formating_homas(hotel, hotel_id, provider, city_id, target_city[1])
                                # Cek apakah file dengan kota tsb sdah ada di memory?
                                # same_name = filter(lambda x: x['name'] == hotel_fmt['name'], cache_content)
                                same_name = self.advance_find_similar_name(hotel_fmt['name'], hotel_fmt['location']['city'], cache_content)
                                if same_name:
                                    # tambahkan detail ke record yg sama tersebut
                                    hotel_id -= 1
                                    if hotel.get('external_code'):
                                        same_name[0]['external_code'][self.masking_provider(provider)] = str(hotel['external_code'][self.masking_provider(provider)] )
                                    else:
                                        same_name[0]['external_code'][self.masking_provider(provider)] = hotel['id']
                                    same_name[0]['images'] += hotel_fmt['images']
                                    if len(same_name[0]['facilities']) < len(hotel_fmt['facilities']):
                                        same_name[0]['facilities'] = hotel_fmt['facilities']
                                    self.file_log_write('Sync: ' + hotel_fmt['name'] + '->' + same_name[0]['name'])
                                    new_to_add_list2.append([
                                        'sync', hotel_fmt['name'].encode("utf-8"),
                                        same_name[0]['name'].encode("utf-8")
                                    ])
                                else:
                                    # create baru di memory
                                    cache_content.append(hotel_fmt)
                                    self.file_log_write('New : ' + hotel_fmt['name'])
                                    new_to_add_list2.append(['new', hotel_fmt['name'].encode("utf-8"),''])
                        f2.close()
                    except Exception as e:
                        self.file_log_write('Error:' + provider + ' in id ' + str(hotel_id) + '; MSG:' + str(e))
                        try:
                            new_to_add_list.append(0)
                            f2.close()
                            pass
                        except:
                            pass

                if cache_content:
                    self.file_log_write('Render ' + target_city[1] + ' End, Get:' + str(len(cache_content)) + ' Hotel(s)')
                    # Print hasil
                    filename = "/var/log/cache_hotel/cache_hotel_" + str(target_city_index) + ".txt"
                    file = open(filename, 'w')
                    file.write(json.dumps(cache_content))
                    file.close()

                    target_city_index += 1
                new_to_add_list.append(len(cache_content) if cache_content else 0)
                need_to_add_list.append(new_to_add_list)
        f.close()
        with open('/var/log/cache_hotel/result log/merger_process_result.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

        with open('/var/log/cache_hotel/result log/merger_history.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(new_to_add_list2)
        csvFile.close()

        self.file_log_write('=================================')
        self.file_log_write('==  Cache Hotel for Homas DONE ==')
        self.file_log_write('=================================')

    # Get Record From HOMAS, Single Vendor
    def get_record_homas(self):
        # Read CSV CITY
        target_city_index = 0
        hotel_id = 0
        rendered_city = []

        # provider_list = ['hotelspro', 'hotelspro_file', 'fitruums', 'webbeds_pool', 'webbeds_excel_pool',
        #                  'itank', 'quantum', 'quantum_pool', 'mgholiday', 'mg_pool', 'miki_api', 'miki_scrap', 'miki_pool',
        #                  'dida_pool', 'tbo', 'oyo']
        provider_list = ['dida_pool', 'fitruums', 'webbeds_pool', 'webbeds_excel_pool']

        need_to_add_list = [['No', 'CityName', 'RodexTrip City_id'] + provider_list + ['Total']]
        new_to_add_list2 = [['Type', 'Name', 'Similar Name']]

        import glob
        for master_provider in provider_list:
            city_ids = glob.glob("/var/log/cache_hotel/"+ master_provider +"/*.json")

            for target_city in city_ids:
                city_name = target_city[22 + len(master_provider):-5]
                if city_name in rendered_city:
                    continue
                cache_content = []
                city_obj = self.env['res.city'].find_city_by_name(city_name)
                city_id = city_obj and city_obj.id or 0
                new_to_add_list = [target_city_index+1, city_name, city_id]
                # Loop All provider
                self.file_log_write(str(target_city_index+1) + '. Start Render: ' + city_name)
                for provider in provider_list:
                    # Looping untuk setiap city di alias name
                    searched_city_names = [city_name,]
                    if city_obj:
                        searched_city_names += [rec.name for rec in city_obj.other_name_ids.filtered(lambda x: x.name not in city_name)]
                    for searched_city_name in searched_city_names:
                        a = 0
                        try:
                            file_url = "/var/log/cache_hotel/" + provider + "/" + searched_city_name + ".json"
                            # Loop untuk setiap city cari file yg nama nya sma dengan  city yg dimaksud
                            with open(file_url, 'r') as f2:
                                file = f2.read()
                                self.file_log_write('Provider ' + provider + ': ' + str(len(json.loads(file))))
                                a += len(json.loads(file))
                                for hotel in json.loads(file):
                                    hotel_id += 1
                                    # rubah format ke odoo
                                    hotel_fmt = self.formating_homas(hotel, hotel_id, provider, city_id, target_city)
                                    # Cek apakah file dengan kota tsb sdah ada di memory?
                                    same_name = self.advance_find_similar_name(hotel_fmt['name'], hotel_fmt['location']['city'], cache_content)
                                    # same_name = False
                                    if same_name:
                                        # tambahkan detail ke record yg sama tersebut
                                        hotel_id -= 1
                                        if hotel.get('external_code'):
                                            same_name[0]['external_code'][self.masking_provider(provider)] = str(hotel['external_code'][self.masking_provider(provider)] )
                                        else:
                                            same_name[0]['external_code'][self.masking_provider(provider)] = hotel['id']
                                        same_name[0]['images'] += hotel_fmt['images']
                                        if len(same_name[0]['facilities']) < len(hotel_fmt['facilities']):
                                            same_name[0]['facilities'] = hotel_fmt['facilities']
                                        self.file_log_write('Sync: ' + hotel_fmt['name'] + '->' + same_name[0]['name'])
                                        new_to_add_list2.append([
                                            'sync', hotel_fmt['name'].encode("utf-8"),
                                            same_name[0]['name'].encode("utf-8")
                                        ])
                                    else:
                                        # create baru di memory
                                        cache_content.append(hotel_fmt)
                                        self.file_log_write('New : ' + hotel_fmt['name'])
                                        new_to_add_list2.append(['new', hotel_fmt['name'].encode("utf-8"),''])
                            f2.close()
                        except Exception as e:
                            self.file_log_write('Error:' + provider + ' in id ' + str(hotel_id) + '; MSG:' + str(e))
                            try:
                                f2.close()
                                pass
                            except:
                                pass
                        new_to_add_list.append(a)

                if cache_content:
                    self.file_log_write('Render ' + city_name + ' End, Get:' + str(len(cache_content)) + ' Hotel(s)')
                    # Print hasil
                    filename = "/var/log/cache_hotel/cache_hotel_" + str(target_city_index) + ".txt"
                    file = open(filename, 'w')
                    file.write(json.dumps(cache_content))
                    file.close()
                    # Simpan di rendered hotel
                    for rec in searched_city_names:
                        # Simpan all alias name juga
                        rendered_city.append(rec)

                    target_city_index += 1
                new_to_add_list.append(len(cache_content) if cache_content else 0)
                need_to_add_list.append(new_to_add_list)

                if target_city_index % 50 == 0:
                    # Simpan record tiap 50 city
                    with open('/var/log/cache_hotel/result log/merger_process_result.csv', 'w') as csvFile:
                        writer = csv.writer(csvFile)
                        writer.writerows(need_to_add_list)
                    csvFile.close()

                    with open('/var/log/cache_hotel/result log/merger_history.csv', 'w') as csvFile:
                        writer = csv.writer(csvFile)
                        writer.writerows(new_to_add_list2)
                    csvFile.close()

        with open('/var/log/cache_hotel/result log/merger_process_result.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

        with open('/var/log/cache_hotel/result log/merger_history.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(new_to_add_list2)
        csvFile.close()

    # Cek setiap record HOMAS FIND yg data2x e kurang
    # Return dari file ini adalah jumlah
    def get_homas_data_status(self):
        target_city_index = 1
        self.file_log_write('=================================')
        self.file_log_write('== Cek Kelengkapan Homas START ==')
        self.file_log_write('=================================')

        rec_number = 1
        need_to_add_list = [['No','Name','File Number','Adress','Rating','images','Facilities','exist']]
        while target_city_index:
            filename = "/var/log/cache_hotel/cache_hotel_" + str(target_city_index) + ".txt"
            scrapped_hotel = []

            with open(filename, 'r') as file:
                file_content = json.loads(file.read())
                for rec in file_content:
                    full_rec = False
                    # Tidak ada nama tidak bisa proses booking.com
                    if rec.get('name') and rec['name'] != 'None' and rec.get('facilities'):
                        if rec.get('images') and isinstance(rec['facilities'], list) and rec['location']['address'] and rec['rating'] != 0:
                            full_rec = True

                    need_to_add_list.append([rec_number,
                                             rec['name'].encode("utf-8"),
                                             target_city_index,
                                             rec['location']['address'].encode("utf-8"),
                                             rec['rating'], rec.get('images') and True or False,
                                             rec.get('facilities') and True or False, full_rec])
                    rec_number += 1
            file.close()
            # Next File
            target_city_index += 1

            # Simpan Scrapped Hotel sebagai record di folder booking_com
            _logger.info("Write File " + rec['location']['city'])
            filename = "/var/log/cache_hotel/booking_com/" + rec['location']['city'] + ".json"
            file = open(filename, 'w')
            file.write(json.dumps(scrapped_hotel))
            file.close()

        self.file_log_write('=================================')
        self.file_log_write('==  Cek Kelengkapan Homas DONE ==')
        self.file_log_write('=================================')

        with open('/var/log/cache_hotel/result log/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    def control_excel(self):
        import copy
        cache_content = []
        filename = "/var/log/cache_hotel/klook_themepark/klook_mapped.csv"
        with open(filename, 'r') as file:
            city_ids = csv.reader(file)
            for city in city_ids:
                a = city[4].split(' & ')
                for city_name in a:
                    if len(a) > 1:
                        pass
                    for city_name1 in city_name.split(' and '):
                        if len(city_name.split(' and ')) > 1:
                            pass
                        new_city = copy.deepcopy(city)
                        new_city[4] = city_name1
                        cache_content.append(new_city)
        file.close()

        with open("/var/log/cache_hotel/klook_themepark/klook_mapped_fmt.csv", 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(cache_content)
        csvFile.close()

    def get_homas_by_some_vendor(self):
        cache_content = []
        self.file_log_write('=================================')
        self.file_log_write('== Cek Kelengkapan Homas START ==')
        self.file_log_write('=================================')
        try:
            filename = "/var/log/cache_hotel/cache_hotel_267.txt"
            with open(filename, 'r') as file:
                file_content = json.loads(file.read())
                for rec in file_content:
                    if 'A5' in rec['external_code'].keys():
                        cache_content.append(rec)
            file.close()
        except Exception as e:
            self.file_log_write(str(e))
        self.file_log_write('=================================')
        self.file_log_write('==  Cek Kelengkapan Homas DONE ==')
        self.file_log_write('=================================')
        filename = "/var/log/cache_hotel/result log/selected_by_provider.json"
        file = open(filename, 'w')
        file.write(json.dumps(cache_content))
        file.close()

    def replace_city_homas(self):
        self.file_log_write('=================================')
        self.file_log_write('== Replace City Homas START ==')
        self.file_log_write('=================================')
        filename = "/var/log/cache_hotel1/cache_hotel_268.txt"
        a = []
        try:
            with open(filename, 'r') as file:
                file_content = json.loads(file.read())
                for rec in file_content:
                    # if rec['location']['city_id'] not in a:
                    #     a.append(rec['location']['city_id'])
                    rec['location']['city_id'] = 573
            file.close()
        except Exception as e:
            self.file_log_write(str(e))
        self.file_log_write('=================================')
        self.file_log_write('==  Replace City Homas DONE    ==')
        self.file_log_write('=================================')
        file = open(filename, 'w')
        file.write(json.dumps(file_content))
        file.close()
    # Ambil Master record yg telah terbentuk
    # Masukan source yg di mau ke master record
    # On Progress
    def merge_record_for_some_source(self):
        # Baca City CSV
        target_city_index = 0
        with open('/var/log/cache_hotel/res_country_city.csv', 'r') as f:
            city_ids = csv.reader(f)
            for target_city in city_ids:
                if target_city_index == 0:
                    target_city_index += 1
                    continue
                cache_content = []

        f.close()
        # Cari nomer file untuk city tsb
        # Baca File + merge data source untuk city tsb
        # Updata CSV Result merger (Nice to have)
        return True

    # ====================== Cache Hotel to Gateway ==============================================
    @api.multi
    def prepare_gateway_cache(self):
        API_CN_HOTEL.signin()
        file_number = 1
        while file_number:
            try:
                name = "cache_hotel_" + str(file_number-1) + ".txt"
                file = open("/var/log/cache_hotel/" + name, 'r')
                content = file.read()
                file.close()
                API_CN_HOTEL.send_request('create_hotel_file', {'name': name, 'content': content})
            except:
                API_CN_HOTEL.send_request('prepare_gateway_cache', {
                    'hotel_ids': [],
                    'city_ids': self.env['test.search'].render_cache_city(),
                    'country_ids': self.env['test.search'].prepare_countries(self.env['res.country'].sudo().search([])),
                    'landmark_ids': []
                })
                break
            file_number += 1

    @api.multi
    def prepare_gateway_destination(self):
        API_CN_HOTEL.send_request('prepare_gateway_cache', {
            'hotel_ids': [],
            'city_ids': self.env['test.search'].render_cache_city(),
            'country_ids': self.env['test.search'].prepare_countries(self.env['res.country'].sudo().search([])),
            'landmark_ids': []
        })