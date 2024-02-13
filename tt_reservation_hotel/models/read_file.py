from odoo import api, fields, models, _
import json
import logging
import xlrd
from .ApiConnector_Hotel import ApiConnectorHotels
import csv, glob, os
from lxml import html
from ...tools import xmltodict
import csv, math
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
API_CN_HOTEL = ApiConnectorHotels()


class HotelInformation(models.Model):
    _inherit = 'tt.hotel'

    # HotelsPro Ver1
    # Masih gabung
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

    # HotelsPro: Ver2
    # Step 01: Ambil smua master(hotel_type, fac, country, destinations)
    # Step 1a: Simpan dalam bentuk File
    def get_record_by_file_2(self):
        url = '/var/log/cache_hotel/hotelspro_file/data/'

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

        filename = "/var/log/cache_hotel/hotelspro_file/master/master_info.txt"
        file = open(filename, 'w')
        file.write(json.dumps(cache_hotel))
        file.close()

    def get_record_by_file_2a(self):
        url = '/var/log/cache_hotel/hotelspro_file/data/'

        breaker = 0
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
                    breaker = 0
                except IOError as e:
                    _logger.error("Couldn't open or write to file (%s)." % e)
                    number += 1
                    breaker += 1
                    if breaker == 3:
                        break

        filename = "/var/log/cache_hotel/hotelspro_file/master/master_dest.txt"
        file = open(filename, 'w')
        file.write(json.dumps(cache_hotel))
        file.close()

    # HotelsPro: Read smua file hotel dan map per city
    def get_record_by_file_3(self):
        # Step 1b: Load cache
        with open("/var/log/cache_hotel/hotelspro_file/master/master_info.txt") as f:
            cache_data = json.load(f)
            cache_type = cache_data['hoteltypes']
            cache_fac = cache_data['facilities']
            cache_country = cache_data['country']
        f.close()
        # Step 02: Buat smua file dari city
        with open("/var/log/cache_hotel/hotelspro_file/master/master_dest.txt") as f:
            cache_city = json.load(f)
        f.close()
        # Step 03: Loop untuk smua file hotel
        # Step 04: mapping berdasarkan city
        url = '/var/log/cache_hotel/hotelspro_file/data/'

        cache_hotel = {}
        filename = 'hotels-'
        number = 1
        counter_false = 0
        while number:
            try:
                # Perlu tambah ini karena data baru dari hotelpro bisa loncat2x (1,3,4,5,7,8)
                _logger.info("Opening file " + url + filename + str(number) + '.json')
                with open(url + filename + str(number) + '.json') as f:
                    data = json.load(f)
                    for obj in data:
                        if cache_city.get(obj.get('destination')):
                            city_name = cache_city[obj['destination']].replace('/', '-').replace("\'", '-') or ''
                        else:
                            # _logger.info("Skipping: Destination" + obj.get('destination'))
                            city_name = 'other'

                        if not cache_hotel.get(city_name):
                            cache_hotel[city_name] = []
                        # _logger.info("Process: " + json.dumps(obj))
                        cache_hotel[city_name].append({
                            'id': obj.get('code'),
                            'name': obj['name'],
                            'street': obj.get('address') and obj['address'] or '',
                            'description': obj.get('descriptions') and obj['descriptions'].get('hotel_information'),
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
                            temp_filename = "/var/log/cache_hotel/hotelspro_file/" + rec + ".json"
                            try:
                                with open(temp_filename, 'r') as f2:
                                    a = f2.read()
                                    old_record = json.loads(a)
                                    old_record += cache_hotel[rec]
                                f2.close()
                            except:
                                old_record = cache_hotel[rec]

                            file = open(temp_filename, 'w')
                            file.write(json.dumps(old_record))
                            file.close()
                        cache_hotel = {}
                counter_false = 0
            except IOError as e:
                _logger.error("Couldn't open or write to file (%s)." % e)
                counter_false += 1
                if counter_false == 3:
                    for rec in cache_hotel.keys():
                        filename = "/var/log/tour_travel/hotelspro_file/" + str(rec) + ".json"
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
            number += 1

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
        with open('/var/log/cache_hotel/quantum_pool/master/Hotels20200728.csv', 'r') as f:
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
        provider_id = self.env['tt.provider'].search([('code', '=', 'itank')], limit=1)
        api_context = {
            'co_uid': self.env.user.id
        }
        search_req = {
            'provider': 'itank',
            'type': 'city',
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
                    for gw_rec in a['response']['Cities']:
                        _logger.info("City: " + gw_rec['CityName'] + ".")
                        need_to_add_list.append([gw_rec['CityCode'], gw_rec['CityName'].encode("utf-8"),
                                                 gw_rec['CityLongName'].encode("utf-8"),
                                                 gw_rec['CountryCode'] ])

                    with open('/var/log/cache_hotel/dida_pool/master/City.csv', 'w') as csvFile:
                        writer = csv.writer(csvFile)
                        writer.writerows(need_to_add_list)
                    csvFile.close()
                except:
                    _logger.info("No City for: " + rec[1] + ".")
                    continue
        f.close()
        _logger.info("=== Processing City END ===")

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
                    _logger.info("City: " + city + ' Get:' + str(len(hotel_list[city])) + ' Hotel(s)')
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
        stopper = 0
        rendered_city = []
        need_to_add_list = []
        try:
            with open("/var/log/cache_hotel/tbo/master_csv/result_data.csv", 'r') as file:
                file_content = csv.reader(file)
                for rec in file_content:
                    i += 1
                    rendered_city.append(rec[1].lower())
                    need_to_add_list.append(rec)
                file.close()
        except:
            need_to_add_list.append(['No', 'City', 'City Code', 'Country', 'Hotel qty'])

        file_content = glob.glob("/var/log/cache_hotel/tbo/master/*.txt")
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

                _logger.info("Get "+str(length)+" Hotel(s) for City: " + city['name'] + ', ' + rec[32:-4])
                need_to_add_list.append([i, city['name'].split(',')[0], city['code'], rec[32:-4], length])
                filename = "/var/log/cache_hotel/tbo/" + city['name'].split(',')[0].replace('/', '-') + ".json"

                i += 1
                # Create Record Hotel per City
                file = open(filename, 'w')
                file.write(json.dumps(hotel_fmt))
                file.close()

                # Save per City
                with open('/var/log/cache_hotel/tbo/master_csv/result_data.csv', 'w') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerows(need_to_add_list)
                csvFile.close()
        return True

    # TBO Holidays
    # Re-Get Hotel yg 0 maupun -1
    def get_record_by_api9b(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        with open("/var/log/cache_hotel/tbo/master_csv/result_data.csv", 'r') as file:
            file_content = csv.reader(file)
            for rec in file_content:
                # Sementara di set 0 dan -1 karena data lama try except return nya 0
                # Per tanggal 13 maret 2020 error diganti -1
                if rec[-1] < 1: #Bisa di ganti 0 jika mau render yg error only (-1)
                    search_req = {
                        'provider': 'tbo',
                        'type': 'hotel',
                        'limit': '',
                        'offset': '',
                        'codes': rec[2],
                    }
                    hotel_fmt = []
                    try:
                        hotel_objs = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                        hotel_fmt = hotel_objs[1]
                        length = len(hotel_fmt)
                    except:
                        length = -1

                    rec[-1] = length
                    if length > 0:
                        _logger.info("Update " + str(length) + " Hotel(s) for City: " + rec[1] + ', ' + rec[3])
                        filename = "/var/log/cache_hotel/tbo/" + rec[1] + ".json"
                        file = open(filename, 'w')
                        file.write(json.dumps(hotel_fmt))
                        file.close()
                    elif length == 0:
                        _logger.info("Empty Hotel(s) for City: " + rec[1] + ', ' + rec[3])
                    else:
                        _logger.info("Error get data for City: " + rec[1] + ', ' + rec[3])

                # Save per City
                with open('/var/log/cache_hotel/tbo/master_csv/result_data.csv', 'w') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerows(file_content)
                csvFile.close()
            file.close()
        return True

    # OYO TMC
    # Get All Hotel (by hotel Code/ 'IN')
    def get_record_by_api10(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        # country_list = [rec.code for rec in self.env['res.country'].search([]) if rec.code]
        country_list = ['ID']
        for rec in country_list:
            i = 1
            limit = 100
            all_obj = (i*limit)+1
            while i*limit < all_obj:
                search_req = {
                    'provider': 'oyo',
                    'type': 'hotel',
                    'limit': limit,
                    'offset': i*limit,
                    'codes': rec, #Country Code
                }
                hotel_fmt = []

                try:
                    hotel_objs = API_CN_HOTEL.get_record_by_api(search_req, api_context)
                    all_obj = hotel_objs[0]
                    hotel_fmt = hotel_objs[1]
                except:
                    _logger.info("Error while Processing Country " + rec)
                    all_obj = 0

                filename = "/var/log/cache_hotel/oyo/master/" + rec + '_' + str(i) + ".json"
                i += 1
                # Create Record Hotel per City
                file = open(filename, 'w')
                file.write(json.dumps(hotel_fmt))
                file.close()
            _logger.info("Get Hotel for Country " + rec + " END get " + str(all_obj) + " Hotel(s)")
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
                rec['city'] = rec['city'].replace('Kabupaten ', '')
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

    # Hotel RodexTrip
    # AutoComplete Cache
    def get_record_by_api13(self):
        api_context = {
            'co_uid': self.env.user.id
        }

        search_req = {
            'provider': 'rodextrip_hotel',
            'type': 'cache',
            'limit': 0,
            'offset': 99999,
            'codes': '',
        }
        hotel_objs = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        return True

    # Klik and Book get new
    def get_record_by_api14(self):
        api_context = {
            'co_uid': self.env.user.id
        }

        search_req = {
            'provider': 'knb',
            'type': 'cache',
            'limit': 0,
            'offset': 99999,
            'codes': '',
        }
        hotel_objs = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        for rec in hotel_objs.keys():
            filename = "/var/log/cache_hotel/knb/master/" + rec + ".json"
            # Create Record Hotel per City
            file = open(filename, 'w')
            file.write(hotel_objs[rec][0])
            file.close()

            filename = "/var/log/cache_hotel/knb/" + rec + ".json"
            # Create Record Hotel per City
            file = open(filename, 'w')
            file.write(hotel_objs[rec][1])
            file.close()
        return True

    # Klik and Book get already exist
    # Not Done Yet
    def get_record_by_api14b(self):
        api_context = {
            'co_uid': self.env.user.id
        }

        search_req = {
            'provider': 'knb',
            'type': 'cache',
            'limit': 0,
            'offset': 99999,
            'codes': '',
        }
        hotel_objs = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        for rec in hotel_objs.keys():
            filename = "/var/log/cache_hotel/knb/master/" + rec + ".json"
            # Create Record Hotel per City
            file = open(filename, 'w')
            file.write(hotel_objs[rec][0])
            file.close()

            filename = "/var/log/cache_hotel/knb/" + rec + ".json"
            # Create Record Hotel per City
            file = open(filename, 'w')
            file.write(hotel_objs[rec][1])
            file.close()
        return True

    # Render from master data
    def get_record_by_api14c(self):
        need_to_add_list = [['No', 'City', 'Country', 'Hotel qty']]
        # Find all xls file in selected directory
        path = '/var/log/cache_hotel/knb/master/'
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
                _logger.info("City: " + city + ' Get:' + str(len(hotel_list[city])) + ' Hotel(s)')
                filename = "/var/log/cache_hotel/knb/" + city.strip().split('/')[0] + ".json"
                file = open(filename, 'w')
                file.write(json.dumps(hotel_list[city]))
                file.close()

                need_to_add_list.append([1, hotel_list[city].encode("utf-8"),
                                         country_file.split('/')[-1].split('_')[2].encode("utf-8"),
                                         len(hotel_list[city])])

        with open('/var/log/cache_hotel/knb/result/Result.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    # Render from master data Excel
    def get_record_by_api14d(self):
        need_to_add_list = [['No', 'City', 'Country', 'Hotel qty']]
        # Find all xls file in selected directory
        path = '/var/log/cache_hotel/knb/'
        _logger.info("========================================")
        _logger.info("Read File in path " + path)
        _logger.info("========================================")

        city_ids = {}
        start_line = 0

        # Baca file
        with open(path + 'master/hotel profile_kliknbook_20200302.csv', 'r') as f:
            file_content = csv.reader(f)
            for idx, rec in enumerate(file_content):
                if idx < start_line:
                    continue
                if not city_ids.get(rec[8]):
                    city_ids[rec[8]] = []
                _logger.info(str(idx) + ". Render " + rec[1] + " in City: " + rec[8])
                city_ids[rec[8]].append({
                    'id': rec[0],
                    'name': rec[1],
                    'street': rec[3],
                    'street2': rec[4],
                    'street3': rec[5],
                    'description': rec[17] + ' ' + rec[18],
                    'email': rec[15],
                    'images': [],
                    # 'facilities': rec[18], #Ada Kolom facility tapi isie string descripsi,
                    'facilities': [], #Jadi isi dari field facility kita masukan ke description
                    'phone': rec[13],
                    'fax': rec[14],
                    'zip': rec[6],
                    'website': rec[16],
                    'lat': '',
                    'long': '',
                    'rating': rec[19] or 0,
                    'hotel_type': '',
                    'city': rec[8],
                })
        f.close()

        need_to_add_list = []
        for idx, city in enumerate(city_ids.keys()):
            file = open(path + city + '.json', 'w')
            need_to_add_list.append([idx, city, len(city_ids[city])])
            file.write(json.dumps(city_ids[city]))
            file.close()

        with open('/var/log/cache_hotel/knb/result/Result.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    # Render from master data Excel 19 Maret 2020 (All City)
    def get_record_by_api14e(self):
        # Find all xls file in selected directory
        path = '/var/log/cache_hotel/knb_all/'
        _logger.info("========================================")
        _logger.info("Read File in path " + path)
        _logger.info("========================================")

        city_ids = {}
        start_line = 1

        # Baca file
        import glob

        file_names = glob.glob(path + "master/*.csv")
        for file_name in file_names:
            with open(file_name, 'r') as f:
                file_content = csv.reader(f)
                for idx, rec in enumerate(file_content):
                    if idx < start_line:
                        continue
                    if not city_ids.get(rec[8]):
                        city_ids[rec[8]] = []
                    _logger.info(str(idx) + ". Render " + rec[1] + " in City: " + rec[8])
                    city_ids[rec[8]].append({
                        'id': rec[0],
                        'name': rec[1],
                        'street': rec[3],
                        'street2': rec[4],
                        'street3': rec[5],
                        'description': rec[17] + ' ' + rec[18],
                        'email': rec[15],
                        'images': [],
                        # 'facilities': rec[18], #Ada Kolom facility tapi isie string descripsi,
                        'facilities': [],  # Jadi isi dari field facility kita masukan ke description
                        'phone': rec[13],
                        'fax': rec[14],
                        'zip': rec[6],
                        'website': rec[16],
                        'lat': '',
                        'long': '',
                        'rating': rec[19] or 0,
                        'hotel_type': '',
                        'city': rec[8],
                    })
            f.close()

        need_to_add_list = [['No', 'City', 'Hotel qty']]
        for idx, city in enumerate(city_ids.keys()):
            city_name = city.replace('/',' ')
            file = open(path + city_name + '.json', 'w')
            need_to_add_list.append([idx, city_name, len(city_ids[city])])
            file.write(json.dumps(city_ids[city]))
            file.close()

        with open('/var/log/cache_hotel/knb_all/result/Result.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    # Render from master data Excel
    # Versi ini hanya untuk updating data jadi dia tidak langsung buat city baru tpi lebih kearah baca
    # compare ID nya ada tidak jika ada ganti info nya
    # jika tidak buat record baru
    # Jika city tidak terdaftar baru buat file kota baru
    def get_record_by_api14f(self):
        path = '/var/log/cache_hotel/knb/'
        _logger.info("========================================")
        _logger.info("Read File in path " + path)
        _logger.info("========================================")

        city_ids = {}
        start_line = 1

        # Baca file
        import glob
        file_names = glob.glob(path + "master/RODE_hotel_Indonesia_20200623155519.csv")
        for file_name in file_names:
            with open(file_name, 'r') as f:
                file_content = csv.reader(f, delimiter=';')
                for idx, rec in enumerate(file_content):
                    if idx < start_line:
                        continue
                    if not city_ids.get(rec[8]):
                        city_ids[rec[8]] = []
                    _logger.info(str(idx) + ". Render " + rec[1] + " in City: " + rec[8])
                    city_ids[rec[8]].append({
                        'id': rec[0],
                        'name': rec[1],
                        'street': rec[3],
                        'street2': rec[4],
                        'street3': rec[5],
                        'description': rec[17] + ' ' + rec[18],
                        'email': rec[15],
                        'images': [],
                        # 'facilities': rec[18], #Ada Kolom facility tapi isie string descripsi,
                        'facilities': [],  # Jadi isi dari field facility kita masukan ke description
                        'phone': rec[13],
                        'fax': rec[14],
                        'zip': rec[6],
                        'website': rec[16],
                        'lat': rec[20],
                        'long': rec[21],
                        'rating': rec[19] or 0,
                        'hotel_type': '',
                        'city': rec[8],
                    })
            f.close()

        need_to_add_list = [['No', 'City', 'Old Rec.', 'New', 'Updated', 'Current Rec.']]
        for idx, city in enumerate(city_ids.keys()):
            for city_name in city.split('/'):
                filename = path + city_name + '.json'
                old_qty = 0
                new_qty = 0
                update_qty = 0
                total_qty = 0
                try:
                    with open(filename, 'r') as file:
                        file_content = json.loads(file.read())
                        old_qty = len(file_content)
                        for hotel_in_file in file_content:
                            new_hotel = True
                            for hotel_in_cache in city_ids[city]:
                                if hotel_in_file['id'] == hotel_in_cache['id']:
                                    hotel_in_file.update(hotel_in_cache)
                                    new_hotel = False
                                    update_qty += 1
                                    break
                            if new_hotel:
                                file_content.append(hotel_in_cache)
                        file.close()
                    new_qty = len(file_content) - update_qty
                    total_qty = len(file_content)
                    file = open(filename, 'w')
                    file.write(json.dumps(file_content))
                    file.close()
                except:
                    file = open(filename, 'w')
                    file.write(json.dumps(city_ids[city]))
                    file.close()
                need_to_add_list.append([idx, city_name, old_qty, new_qty, update_qty, total_qty])
            # if '/' in city:
            #     city_name = city.replace('/', ' ')
            #     file = open(path + city_name + '.json', 'w')
            #     need_to_add_list.append([idx, city_name, len(city_ids[city])])
            #     file.write(json.dumps(city_ids[city]))
            #     file.close()


        with open('/var/log/cache_hotel/knb_all/result/Result.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

    # ====================== TOOLS =====================================================
    def masking_provider(self, provider):
        # Perlu dibuat gini karena cache data bisa berasal dari mana sja
        # EXAMPLE: mg_pool, miki_api, hotelspro_file, dida_pool dll
        provider = provider.split('_')[0]
        if provider in ['mg', 'mgholiday', 'mgjarvis']:
            return 'A1'
        elif provider == 'dida':
            return 'A2'
        elif provider == 'knb':
            return 'A3'
        elif provider == 'miki':
            return 'A4'
        elif provider == 'quantum':
            return 'A5'
        elif provider in ['webbeds', 'fitruums']:
            return 'A6'
        elif provider == 'hotelbeds':
            return 'A7'
        elif provider == 'hotelspro':
            return 'A8'
        elif provider == 'tbo':
            return 'A9'
        elif provider == 'welcomebeds':
            return 'A10'
        elif provider == 'oyo':
            return 'A11'
        elif provider == 'itank':
            return 'A12'
        elif provider == 'rodextrip_hotel':
            return 'A13'
        elif provider == 'traveloka':
            return 'A14'
        elif provider == 'from':
            return 'A3'
        else:
            return provider

    def compute_related_city(self, city_obj, city_name=''):
        city_name = city_name or city_obj.name

        searched_city_ids = [city_obj.id]
        searched_city_ids += [rec.id for rec in city_obj.other_name_ids.filtered(lambda x: x.name not in city_name)]

        state_obj = self.env['res.country.state'].search([('name', '=ilike', city_name)], limit=1)
        if state_obj:
            searched_city_ids += state_obj.city_ids.ids

        return searched_city_ids

    def comp_fac(self):
        # for fac in new_hotel.get('facilities') or []:
        #     if isinstance(fac, dict):
        #         if not fac.get('facility_name'):
        #             fac['facility_name'] = fac.pop('name')
        #         fac_name = fac['facility_name']
        #     else:
        #         fac_name = fac
        #         fac = {
        #             'facility_name': fac,
        #             'facility_id': False,
        #         }
        #     for fac_det in fac_name.split('/'):
        #         facility = self.env['tt.hotel.facility'].search([('name', '=ilike', fac_det)])
        #         if facility:
        #             fac['facility_id'] = facility[0].internal_code
        #             break
        #         else:
        #             facility = self.env['tt.provider.code'].search([('name', '=ilike', fac_det), ('facility_id', '!=', False)])
        #             if facility:
        #                 fac['facility_id'] = facility[0].facility_id.internal_code
        #                 break
        #
        #             # Rekap Facility Other Name
        #             with open('/var/log/cache_hotel/result log/master/new_facility.csv', 'a') as csvFile:
        #                 writer = csv.writer(csvFile)
        #                 writer.writerows([[provider, fac_det]])
        #             csvFile.close()
        return True

    def formating_homas(self, hotel, hotel_id, provider, city_id, city_name, destination_id=False, country_id=False):
        loc_obj = hotel.get('location') or hotel
        new_hotel = {
                    'id': str(hotel_id),
                    'name': hotel.get('name') and hotel['name'].title(),
                    'rating': hotel.get('rating', 0),
                    'prices': [],
                    'description': hotel.get('description'),
                    'location': {
                        'destination_id': destination_id,
                        'city_id': isinstance(city_id, int) and city_id or city_id.id if city_id else False,
                        'country_id': isinstance(country_id, int) and country_id or country_id.id if city_id else False,
                        'address': loc_obj.get('address') or loc_obj.get('street'),
                        'address2': loc_obj.get('address2') or loc_obj.get('street2'),
                        'address3': loc_obj.get('address3') or loc_obj.get('street3'),
                        'city': loc_obj.get('city') or hotel.get('city', city_name),
                        'state': hotel.get('state_id.name'),
                        'district': hotel.get('district_id'),
                        'kelurahan': hotel.get('kelurahan'),
                        'zipcode': hotel.get('zipcode') or hotel.get('zip')
                    },
                    'telephone': hotel.get('phone'),
                    'fax': hotel.get('fax'),
                    'ribbon': '',
                    'lat': hotel.get('lat'),
                    'long': hotel.get('long'),
                    'state': 'confirm',
                    'external_code': {provider: str(hotel.get('id') or hotel.get('code'))},
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
        provider_id = self.env['tt.provider'].search([('code', '=ilike', provider)], limit=1)
        for img in new_hotel.get('images') or []:
            new_img_url = 'http://photos.hotelbeds.com/giata/bigger/' + img['path']
            fac_list.append({'name': '', 'url': new_img_url, 'description': '', 'provider_id': provider_id.id})

            # if isinstance(img, str):
            #     new_img_url = 'http' in img and img or 'http://www.sunhotels.net/Sunhotels.net/HotelInfo/hotelImage.aspx' + img + '&full=1'
            #     provider_id = self.env['tt.provider'].search([('code', '=ilike', provider)], limit=1)
            #     fac_list.append({'name': '', 'url': new_img_url, 'description': '' , 'provider_id': provider_id.id})
            # else:
            #     # Digunakan hotel yg bisa dpet nama image nya
            #     # Sampai tgl 11-11-2019 yg kyak gini (miki_api) formate sdah bener jadi bisa langsung break
            #     # Lek misal formate beda mesti di format ulang
            #     fac_list = new_hotel['images']
            #     break
        new_hotel['images'] = fac_list

        new_fac = []
        # for fac in new_hotel.get('facilities') or []:
        #     if isinstance(fac, dict):
        #         if not fac.get('facility_name'):
        #             fac['facility_name'] = fac.pop('name')
        #         fac_name = fac['facility_name']
        #     else:
        #         fac_name = fac
        #         fac = {
        #             'facility_name': fac,
        #             'facility_id': False,
        #         }
        #     new_fac.append(fac)
        #     # for fac_det in fac_name.split('/'):
        #     #     facility = self.env['tt.hotel.facility'].search([('name', '=ilike', fac_det)])
        #     #     if facility:
        #     #         fac['facility_id'] = facility[0].internal_code
        #     #         break
        #     #     else:
        #     #         facility = self.env['tt.provider.code'].search([('name', '=ilike', fac_det), ('facility_id', '!=', False)])
        #     #         if facility:
        #     #             fac['facility_id'] = facility[0].facility_id.internal_code
        #     #             break
        #     #
        #     #         # Rekap Facility Other Name
        #     #         with open('/var/log/cache_hotel/result log/master/new_facility.csv', 'a') as csvFile:
        #     #             writer = csv.writer(csvFile)
        #     #             writer.writerows([[provider, fac_det]])
        #     #         csvFile.close()
        new_hotel['facilities'] = new_fac
        return new_hotel

    def formating_homas_jupiter(self, hotel_id, hotel_rec, providers):
        new_hotel = {
                    'id': str(hotel_id),
                    'name': hotel_rec[1].title(),
                    'rating': hotel_rec[19],
                    'prices': [],
                    'description': hotel_rec[17],
                    'location': {
                        'city_id': hotel_rec[8],
                        'address': hotel_rec[2],
                        'city': hotel_rec[8],
                        'state': hotel_rec[3],
                        'district': hotel_rec[4],
                        'kelurahan': hotel_rec[5],
                        'zipcode': hotel_rec[6],
                    },
                    'telephone': hotel_rec[13],
                    'fax': hotel_rec[14],
                    'ribbon': '',
                    'lat': hotel_rec[20],
                    'long': hotel_rec[21],
                    'state': 'confirm',
                    'external_code': {self.masking_provider(providers): str(hotel_rec[0])},
                    'near_by_facility': [],
                    'images': [],
                    'facilities': [],
                }
        # for provider in providers:
        #     new_hotel['external_code'][self.masking_provider(provider[0])] = str(provider[1])
        return new_hotel

    def formatting_hotel_name(self, hotel_name, city_name=False):
        # Comparing Hotel Tunjungan Surabaya dengan Tunjungan Hotel Surabaya
        # 1. Set to lower
        # 2. Split using " "
        fmt_hotel_name = hotel_name.lower()
        for param in ['-', '_', '+', ',', '.', ';', '(', ')']:
            fmt_hotel_name = fmt_hotel_name.replace(param, ' ')
        fmt_hotel_name = fmt_hotel_name.replace('@', 'at ')
        fmt_hotel_name = fmt_hotel_name.replace('   ', ' ')
        fmt_hotel_name = fmt_hotel_name.replace('  ', ' ')
        fmt_hotel_name = fmt_hotel_name.replace('&Amp;', '&')
        fmt_hotel_name = fmt_hotel_name.replace('&amp;', '&')
        fmt_hotel_name = fmt_hotel_name.split(' ')
        # 3. Remove Selected String (Hotel, Motel, Apartement , dsb)
        ext_param = ['hotel', 'hostel', 'motel', 'villa', 'villas', 'apartment', 'and', '&', '&amp;']
        # 4. Remove City Name
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

    def calc_similarity(self, fmt_hotel_name, fmt_hotel_master, city_name):
        if len(fmt_hotel_name) > 3:
            similarity = 0
            for elem in fmt_hotel_name:
                # Contoh "[Vagabond,a,tribute,portofolio]" "A" bikin value ne naik jadi ku skip
                if len(elem) == 1:
                    continue
                # if elem in fmt_hotel_master: #Tidak bisa Handle Grand Setiakawan, Master: Hotel Grand Setia Kawan
                if elem in "".join(fmt_hotel_master):
                    similarity += 1

            len_const = math.floor(max(len(fmt_hotel_name), len(fmt_hotel_master)))
            if similarity >= len_const/2:
                return True
            elif filter(lambda x:x in ['formerly', 'ex'], fmt_hotel_name) and similarity >= len_const/4:
                return True
        else:
            # if all(elem in " ".join(fmt_hotel_master) for elem in fmt_hotel_name): #Tidak bisa Handle Grand Setiakawan, Master: Hotel Grand Setia Kawan
            if all(elem in "".join(fmt_hotel_master) for elem in fmt_hotel_name):
                return True
        return False

    def advance_find_similar_name_from_database(self, hotel_name, city_name, city_ids, destination_id, new_hotel_id, limit=20):
        fmt_hotel_name = self.formatting_hotel_name(hotel_name, city_name)
        temp = []

        if any(x == fmt_hotel_name for x in ['oyo', 'reddoors', 'zen']):
            limit = 80

        # TYPE 1:
        # Sme Nme
        for rec in self.env['tt.hotel.master'].search([('name', '=', hotel_name)], limit=1):
            temp.append(rec)

        # cek by city dulu klo masih kurang => destination
        if city_ids and False not in city_ids:
            # Todo Find City
            # for rec in self.env['tt.hotel'].search([('id', '!=', new_hotel_id), ('city_id', 'in', city_ids), ('state', 'not in', ['merged',])]):
            for rec in self.env['tt.hotel.master'].search([('city_id', 'in', city_ids)]):
                # Remark untuk prod START
                # if 'soloha' in rec.name.lower():
                #     var_test = 'Test'
                # Remark untuk prod END

                if len(temp) > limit:
                    return temp

                if rec not in temp:
                    fmt_hotel_master = self.formatting_hotel_name(rec.name, city_name)
                    if self.calc_similarity(fmt_hotel_name, fmt_hotel_master, city_name):
                        temp.append(rec)

        if destination_id and len(temp) < limit:
            for rec in self.env['tt.hotel.master'].search([('destination_id', '=', destination_id)]):
                if len(temp) > limit:
                    return temp
                if rec not in temp:
                    fmt_hotel_master = self.formatting_hotel_name(rec.name, city_name)
                    if self.calc_similarity(fmt_hotel_name, fmt_hotel_master, city_name):
                        temp.append(rec)
        # TYPE 1: End

        # TYPE 2: Start cek smua barengan
        # params = [('name', '=ilike', hotel_name)]

        # if city_ids:
        #     params.append(('city_id', 'in', city_ids))
        # if destination_id:
        #     params.append(('destination_id', '=', destination_id))
        #
        # new_params = ['|' for x in range(len(params)-1)]
        # new_params += params
        # for rec in self.env['tt.hotel.master'].search(new_params):
        #     if rec not in temp:
        #         temp.append(rec)
        # TYPE 2: End
        return temp

    def advance_find_similar_name_from_database_2(self):
        if not self.destination_id or not self.city_id:
            self.fill_country_city()

        city_ids = self.compute_related_city(self.city_id)
        same_hotel_obj = self.advance_find_similar_name_from_database(self.name, self.city_id.name, city_ids, self.destination_id.id, False)

        if not same_hotel_obj:
            for city_other_name_obj in self.city_id.other_name_ids:
                temp_same_hotel_objs = self.advance_find_similar_name_from_database(self.name, ' '.join([self.city_id.name, city_other_name_obj.name]), city_ids, self.destination_id.id, False)

                for temp_same_hotel_obj in temp_same_hotel_objs:
                    if temp_same_hotel_obj.id not in [x.id for x in same_hotel_obj]:
                        same_hotel_obj.append(temp_same_hotel_obj)

        for same_hotel_obj_id in same_hotel_obj:
            comparing_id = self.env['tt.hotel.compare'].create({
                'hotel_id': self.id,
                'comp_hotel_id': same_hotel_obj_id.id,
            })
            comparing_id.compare_hotel()

    def exact_find_similar_name(self, hotel_name, city_name, cache_content):
        for rec in cache_content:
            if self.formatting_hotel_name(rec['name'], city_name) == self.formatting_hotel_name(hotel_name, city_name):
                return [rec,]
        return False

    def create_hotel(self, hotel_obj, file_number=-1):
        create_hotel_id = self.env['tt.hotel'].create({
            'name': hotel_obj['name'],
            'rating': hotel_obj['rating'],
            'ribbon': hotel_obj['ribbon'],
            'email': hotel_obj.get('email'),
            'website': hotel_obj.get('website'),
            'provider': ', '.join([self.env['tt.provider'].search(['|',('code', '=', xxx),('alias', '=', xxx)], limit=1).name or '' for xxx in
                                   hotel_obj['external_code'].keys()]),
            'description': hotel_obj['description'],
            'lat': hotel_obj['lat'],
            'long': hotel_obj['long'],
            'phone': hotel_obj['telephone'],
            'address': hotel_obj['location']['address'],
            'address2': False,
            'address3': hotel_obj['location']['city'],
            'zip': hotel_obj['location']['zipcode'],
            'city_id': hotel_obj['location']['city_id'],  # Todo search City
            'state_id': hotel_obj['location']['state'],
            'country_id': hotel_obj['location']['country_id'],
            'file_number': file_number,
            'destination_id': hotel_obj['location']['destination_id'],
        })

        # Create Image
        for img in hotel_obj['images']:
            img.update({
                'hotel_id': create_hotel_id.id,
                'provider_id': '',
            })
            if img.get('tag'):
                img.pop('tag') #traveloka
            self.env['tt.hotel.image'].create(img)

        # Create Facility
        fac_link_ids = []
        for fac in hotel_obj['facilities']:
            if fac.get('facility_id'):
                fac_link_ids.append(int(fac['facility_id']))
            else:
                fac_link_ids.append(self.env['tt.hotel.facility'].sudo().find_by_name(fac['facility_name']))
        create_hotel_id.update({'facility_ids': [(6, 0, fac_link_ids)]})

        # Create Landmark
        for landmark in hotel_obj['near_by_facility']:
            continue

        # Create Provider IDS
        for vendor in hotel_obj['external_code'].keys():
            self.env['tt.provider.code'].create({
                'provider_id': self.env['tt.provider'].search(['|',('code', '=', vendor),('alias', '=', vendor)], limit=1).id,
                'code': hotel_obj['external_code'][vendor],
                'res_id': create_hotel_id.id,
                'res_model': 'tt.hotel',
                'name': hotel_obj['name'],
            })
        return create_hotel_id

    def update_hotel(self, create_hotel_id, hotel_obj):
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
                fac_link_ids.append(self.env['tt.hotel.facility'].sudo().find_by_name(fac['facility_name']))
        create_hotel_id.update({
            'facility_ids': [(6, 0, fac_link_ids)],
            'address': hotel_obj['location']['address'],
            'address2': hotel_obj['location']['address2'],
            'address3': hotel_obj['location']['address3'],
            'lat': hotel_obj['lat'],
            'long': hotel_obj['long'],
            'rating': hotel_obj['rating'],
        })
        return create_hotel_id

    def create_or_edit_hotel(self, hotel_obj, file_number=-1, provider_id=False):
        ext_code = list(hotel_obj['external_code'].keys())[0]
        if not provider_id:
            provider_id = self.env['tt.provider'].search(['|',('alias','=', ext_code),('code','=', ext_code)], limit=1).id
        old_objs = self.env['tt.provider.code'].search([('provider_id', '=', provider_id), ('code', '=', hotel_obj['external_code'][ext_code])])

        # Vin: 21082023: Webbeds Code e kembar antara tt.hotel dan tt.hotel.destination
        if old_objs and old_objs[0].res_model == 'tt.hotel':
            self.file_log_write('Skip Update for Hotel ' + str(old_objs[0].name) + ' with code ' + str(old_objs[0].code) )
            return False  # Demo Only
            # self.file_log_write('Update for Hotel ' + str(old_objs[0].name) + ' with code ' + str(old_objs[0].code))
            # new_obj = self.update_hotel(self.env['tt.hotel'].browse(old_objs[0].res_id), hotel_obj)
        else:
            self.file_log_write('Create new Hotel ' + str(hotel_obj['name']) + ' with code ' + str(hotel_obj['external_code'][ext_code]) + ' From ' + ext_code)
            new_obj = self.create_hotel(hotel_obj, file_number)
        return new_obj

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

    def get_rendered_city(self):
        rendered_city = []
        length = 0
        filename = "/var/log/cache_hotel/result log/merger_process_result.csv"
        try:
            with open(filename, 'r') as file:
                city_ids = csv.reader(file)
                for city in city_ids:
                    rendered_city.append(city[1].lower())
            length = city[0]
        except:
            pass
        if len(rendered_city) >= 1:
            return rendered_city[1:], length
        else:
            return rendered_city, length

    # Get Record From HOMAS, all in provider list
    def get_record_homas(self):
        # Read CSV CITY
        rendered_city, len_rendered = self.get_rendered_city()
        target_city_index = int(len_rendered)
        hotel_id = 0

        # provider_list = ['hotelspro_file', ]
        # provider_list = ['hotelspro', 'fitruums', 'webbeds_pool', 'webbeds_excel_pool',
        #                  'itank', 'quantum', 'quantum_pool', 'mgholiday', 'mg_pool', 'miki_api', 'miki_scrap', 'miki_pool',
        #                  'knb', 'knb_all', 'dida_pool', 'tbo', 'oyo']
        provider_list = ['webbeds_pool', 'webbeds_excel_pool', 'quantum', 'quantum_pool', 'miki_api',
                         'miki_scrap', 'miki_pool', 'hotelspro_file', 'hotelspro_scrap', 'knb', 'dida_pool', 'oyo']

        new_to_add_list2 = [['Type', '#1:Name', '#1:address', '#1:provider', '#2:Similar Name', '#2:address', '#2:provider']]
        if not rendered_city:
            need_to_add_list = [['No', 'CityName', 'AliasName', 'RodexTrip City_id'] + provider_list + ['Total', 'Total with Alias']]
        else:
            need_to_add_list = []

        import glob
        for master_provider in provider_list:
            city_ids = glob.glob("/var/log/cache_hotel/"+ master_provider +"/*.json")

            for target_city in city_ids:
                city_name = target_city[22 + len(master_provider):-5]
                if city_name.lower() in rendered_city:
                    continue
                cache_content = []
                city_obj = self.env['res.city'].find_city_by_name(city_name)
                city_id = city_obj and city_obj.id or 0
                # Loop All provider
                self.file_log_write(str(target_city_index+1) + '. Start Render: ' + city_name)
                # Looping untuk setiap city di alias name
                searched_city_names = [city_name, ]
                if city_obj:
                    searched_city_names += [rec.name for rec in city_obj.other_name_ids.filtered(lambda x: x.name not in city_name)]
                new_to_add_list = []
                for searched_city_name in searched_city_names:
                    new_to_add_list_temp = [target_city_index + 1, city_name, searched_city_name, city_id]
                    current_length = len(cache_content)
                    for provider in provider_list:
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
                                    # same_name = self.advance_find_similar_name(hotel_fmt['name'], hotel_fmt['location']['city'], cache_content)
                                    same_name = self.exact_find_similar_name(hotel_fmt['name'], hotel_fmt['location']['city'], cache_content)
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
                                        # self.file_log_write('Sync: ' + hotel_fmt['name'] + '->' + same_name[0]['name'])
                                        add = hotel_fmt['location']['address'] or ''
                                        add2 = same_name[0]['location']['address'] or ''
                                        new_to_add_list2.append([
                                            'sync', hotel_fmt['name'].encode("utf-8"), add.encode("utf-8"), ','.join(hotel_fmt['external_code'].keys()).encode("utf-8"),
                                            same_name[0]['name'].encode("utf-8"), add2.encode("utf-8"), ','.join(same_name[0]['external_code'].keys()).encode("utf-8")
                                        ])
                                    else:
                                        # create baru di memory
                                        cache_content.append(hotel_fmt)
                                        add = hotel_fmt['location']['address'] or ''
                                        # self.file_log_write('New : ' + hotel_fmt['name'])
                                        new_to_add_list2.append(['new', hotel_fmt['name'].encode("utf-8"), add.encode("utf-8"), ','.join(hotel_fmt['external_code'].keys()).encode("utf-8"),
                                                                 ''])
                            f2.close()
                        except Exception as e:
                            self.file_log_write('Error:' + provider + ' in id ' + str(hotel_id) + '; MSG:' + str(e))
                            try:
                                f2.close()
                                pass
                            except:
                                pass
                        new_to_add_list_temp.append(a)
                    new_to_add_list_temp.append(len(cache_content) - current_length)
                    new_to_add_list.append(new_to_add_list_temp)

                if cache_content:
                    self.file_log_write('Render ' + city_name + ' End, Get:' + str(len(cache_content)) + ' Hotel(s)')
                    # Print hasil
                    # filename = "/var/log/cache_hotel/cache_hotel_" + str(target_city_index) + ".txt"
                    filename = "/var/log/tour_travel/cache_hotel/cache_hotel_" + str(target_city_index) + ".txt"
                    file = open(filename, 'w')
                    file.write(json.dumps(cache_content))
                    file.close()
                    # Simpan di rendered hotel
                    for rec in searched_city_names:
                        # Simpan all alias name juga
                        rendered_city.append(rec)

                    target_city_index += 1
                for list_line in new_to_add_list:
                    if list_line == new_to_add_list[-1]:
                        list_line.append(len(cache_content) if cache_content else 0)
                    else:
                        list_line.append(0)
                    need_to_add_list.append(list_line)

                if target_city_index % 10 == 0:
                    # Simpan record tiap 10 city
                    with open('/var/log/cache_hotel/result log/merger_process_result.csv', 'a') as csvFile:
                        writer = csv.writer(csvFile)
                        writer.writerows(need_to_add_list)
                    csvFile.close()
                    need_to_add_list = []

                with open('/var/log/cache_hotel/result log/merger_history_' + city_name + '.csv', 'w') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerows(new_to_add_list2)
                csvFile.close()
                new_to_add_list2 = [['Type', '#1:Name', '#1:address', '#1:provider', '#2:Similar Name', '#2:address', '#2:provider']]


        with open('/var/log/cache_hotel/result log/merger_process_result.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()

        with open('/var/log/cache_hotel/result log/merger_history.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(new_to_add_list2)
        csvFile.close()

        _logger.info('===============================')
        _logger.info('==        RENDER DONE        ==')
        _logger.info('===============================')

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
    # C. Merge to Master
    def merge_record_for_some_source(self):
        provider_list = ['quantum_pool',]
        need_to_add_city = {}
        rendered_city_ids = []

        # Baca City CSV
        with open('/var/log/cache_hotel/result log/merger_process_result.csv', 'r') as f:
            rendered_city_ids = csv.reader(f)
            rendered_city_ids_1 = [target_city for target_city in rendered_city_ids]
            rendered_city_ids = rendered_city_ids_1
        f.close()

        for master_provider in provider_list:
            vendor_city_ids = glob.glob("/var/log/cache_hotel/" + master_provider + "/*.json")
            for vendor_city_url in vendor_city_ids:
                vendor_city = vendor_city_url[22 + len(master_provider):-5]
                with open(vendor_city_url, 'r') as f1:
                    vendor_hotel_objs = f1.read()
                f1.close
                for target_city in rendered_city_ids:
                    if target_city[1].lower() == vendor_city.lower():
                        _logger.info(msg='Processing ' + master_provider + ' From: ' + vendor_city)
                        try:
                            # if vendor_city.lower() == 'surabaya':
                            #     oioioi = ''
                            # Cari nomer file untuk city tsb
                            file_number = int(target_city[0])-1

                            # Baca File + merge data source untuk city tsb
                            # with open('/var/log/cache_hotel/cache_hotel_' + str(file_number) + '.txt', 'r') as f2:
                            with open('/var/log/tour_travel/cache_hotel/cache_hotel_' + str(file_number) + '.txt', 'r') as f2:
                                cache_file = f2.read()
                                cache_content = json.loads(cache_file)
                            f2.close()

                            # merge data source untuk city tsb
                            for vendor_hotel_obj in json.loads(vendor_hotel_objs):
                                hotel_fmt = self.formating_homas(vendor_hotel_obj, vendor_hotel_obj['id'], master_provider, target_city[2], vendor_city)
                                same_name = self.exact_find_similar_name(hotel_fmt['name'], hotel_fmt['location']['city'], cache_content)

                                if same_name:
                                    # tambahkan detail ke record yg sama tersebut
                                    if hotel_fmt.get('external_code'):
                                        same_name[0]['external_code'].update(hotel_fmt['external_code'])
                                    else:
                                        same_name[0]['external_code'][self.masking_provider(master_provider)] = hotel_fmt['id']
                                    same_name[0]['images'] += hotel_fmt['images']
                                    if len(same_name[0]['facilities']) < len(hotel_fmt['facilities']):
                                        same_name[0]['facilities'] = hotel_fmt['facilities']
                                    if not same_name[0]['description']:
                                        same_name[0]['description'] = hotel_fmt['description']
                                else:
                                    # create baru di memory
                                    cache_content.append(hotel_fmt)

                            # Adding data for update CSV Result
                            if not need_to_add_city.get(target_city[1].lower()):
                                need_to_add_city[target_city[1].lower()] = {}
                            need_to_add_city[target_city[1].lower()].update({master_provider: len(json.loads(vendor_hotel_objs)) })
                            need_to_add_city[target_city[1].lower()].update({ 'total': len(cache_content) })

                            file = open('/var/log/tour_travel/cache_hotel/cache_hotel_' + str(file_number) + '.txt', 'w')
                            file.write(json.dumps(cache_content))
                            file.close()

                            _logger.info(msg='Get ' + str(len(json.loads(vendor_hotel_objs))) + ' From: ' + vendor_city + ' Total: ' + str(len(cache_content)))
                            break
                        except:
                            _logger.info(msg='Error While Processing ' + master_provider + ' From: ' + vendor_city)

                # Notif jika city tidak ditemukan
                if not need_to_add_city.get(vendor_city.lower()):
                    if len(json.loads(vendor_hotel_objs)) < 1:
                        _logger.info(msg='Skipping city ' + vendor_city + ' No Hotel Found')
                        continue
                    _logger.info(msg='Create new city ' + vendor_city + ' with ' + str(len(json.loads(vendor_hotel_objs))) + ' Hotel(s)')

                    target_city_index = int(rendered_city_ids[-1][0])
                    # Add hotel file
                    filename = "/var/log/tour_travel/cache_hotel/cache_hotel_" + str(target_city_index) + ".txt"
                    file = open(filename, 'w')
                    file.write(vendor_hotel_objs)
                    file.close()

                    # Update Need to add
                    if not need_to_add_city.get(vendor_city.lower()):
                        need_to_add_city[vendor_city.lower()] = {}
                    need_to_add_city[vendor_city.lower()].update({master_provider: len(json.loads(vendor_hotel_objs))})
                    need_to_add_city[vendor_city.lower()].update({'total': len(json.loads(vendor_hotel_objs))})

                    # Update concurrent cache
                    new_a = [str(target_city_index+1), vendor_city.title()]
                    new_a += [0 for a in range(2, len(rendered_city_ids[0]))]
                    rendered_city_ids.append(new_a)

        # Update Master Result
        idx = 1
        need_to_add = []
        for rec in rendered_city_ids:
            if idx == 1:
                # Re formatting Header result merge
                total_idx = -1
                for idx, total_idxs in enumerate( rec ):
                    if total_idxs.lower() == 'total':
                        total_idx = idx
                        break
                total = rec.pop(total_idx)  # Pop Total
                # Adding provider_list
                rec += provider_list
                rec.append(total)
                need_to_add.append(rec)
                idx = 2
                continue

            add_hotel_qty = [0 for a in provider_list]
            total = rec.pop(total_idx) # Pop Total
            if need_to_add_city.get(rec[1].lower()):
                add_hotel_qty = [need_to_add_city[rec[1].lower()].get(a) and need_to_add_city[rec[1].lower()][a] or 0 for a in provider_list]
                total = need_to_add_city[rec[1].lower()]['total']
            rec += add_hotel_qty
            rec.append(total)
            need_to_add.append(rec)

        with open('/var/log/cache_hotel/result log/merger_process_result_1.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add)
        csvFile.close()
        # Update CSV Result merger (Nice to have)
        return True

    # GateWay bakal catet data search yg tidak terdaftar dan tidak lengkap (no address)
    def merge_record_for_with_search_result(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_list = ['from_cache',]

        render_city = {}
        idx = 1
        need_to_add_list = [['No','Provider','Hotel Id','Hotel Name','Type']]

        # Baca City CSV
        with open('/var/log/cache_hotel/result log/merger_process_result.csv', 'r') as f:
            rendered_city_ids = csv.reader(f)
            for rec in rendered_city_ids:
                render_city[rec[1]] = rec[0]
        f.close()

        for master_provider in provider_list:
            vendor_city_ids = glob.glob(base_cache_directory + master_provider + "/*.json")
            for vendor_city_url in vendor_city_ids:
                vendor_city = vendor_city_url[len(base_cache_directory) + len(master_provider):-5]
                with open(vendor_city_url, 'r') as f1:
                    vendor_hotel_objs = f1.read()
                f1.close()

                _logger.info(msg='Processing Vendor: ' + master_provider + ' From: ' + vendor_city)
                try:
                    # if vendor_city.lower() == 'surabaya':
                    #     oioioi = ''
                    # Cari nomer file untuk city tsb
                    file_number = int(render_city[vendor_city])-1

                    # Baca File + merge data source untuk city tsb
                    # with open('/var/log/cache_hotel/cache_hotel_' + str(file_number) + '.txt', 'r') as f2:
                    with open('/var/log/tour_travel/cache_hotel/cache_hotel_' + str(file_number) + '.txt', 'r') as f2:
                        cache_file = f2.read()
                        cache_content = json.loads(cache_file)
                    f2.close()

                    # merge data source untuk city tsb
                    for vendor_hotel_obj in json.loads(vendor_hotel_objs):
                        master_provider_new = list(vendor_hotel_obj['external_code'].keys())[0]
                        hotel_fmt = self.formating_homas(vendor_hotel_obj, vendor_hotel_obj['id'], master_provider_new, '', vendor_city)
                        same_name = self.exact_find_similar_name(hotel_fmt['name'], hotel_fmt['location']['city'], cache_content)

                        if same_name:
                            # tambahkan detail ke record yg sama tersebut
                            if hotel_fmt.get('external_code'):
                                same_name[0]['external_code'].update(hotel_fmt['external_code'])
                            else:
                                same_name[0]['external_code'][self.masking_provider(master_provider_new)] = hotel_fmt['id']
                            need_to_add_list.append([idx, self.masking_provider(master_provider_new), hotel_fmt['id'], hotel_fmt['name'], 'update'])
                        else:
                            cache_content.append(hotel_fmt)
                            need_to_add_list.append([idx, self.masking_provider(master_provider_new), hotel_fmt['id'], hotel_fmt['name'], 'new'])
                            continue
                        idx += 1

                    # Adding data for update CSV Result

                    file = open('/var/log/tour_travel/cache_hotel/cache_hotel_' + str(file_number) + '.txt', 'w')
                    file.write(json.dumps(cache_content))
                    file.close()

                    _logger.info(msg='Get ' + str(len(json.loads(vendor_hotel_objs))) + ' From: ' + vendor_city + ' Total: ' + str(len(cache_content)))
                except:
                    _logger.info(msg='Error While Processing ' + master_provider + ' From: ' + vendor_city)

        with open('/var/log/cache_hotel/from_cache/master/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add_list)
        csvFile.close()
        return True

    def merge_2_city_result(self):
        # Baca City CSV
        with open('/var/log/cache_hotel/result log/merger_process_result.csv', 'r') as f:
            rendered_city_ids = csv.reader(f)
            rendered_city_ids_1 = [target_city for target_city in rendered_city_ids]
            rendered_city_ids = rendered_city_ids_1
        f.close()
        # Cari Index file using nama city yg ingin di merge
        master_index = 0
        slave_index = 0

        # Baca File untuk master city
        # Baca File untuk slave city (To Be Merge) dan nama kota yg digunakan adalah nama master city nya
        with open('/var/log/cache_hotel/cache_hotel_' + str(master_index) + '.txt', 'r') as f2:
            cache_file = f2.read()
            master_cache_content = json.loads(cache_file)
        f2.close()
        with open('/var/log/cache_hotel/cache_hotel_' + str(slave_index) + '.txt', 'r') as f2:
            cache_file = f2.read()
            slave_cache_content = json.loads(cache_file)
        f2.close()

        for hotel_fmt in slave_cache_content:
            same_name = self.exact_find_similar_name(hotel_fmt['name'], hotel_fmt['location']['city'], master_cache_content)
            if same_name:
                # tambahkan detail ke record yg sama tersebut
                for rec in hotel_fmt['external_code'].keys():
                    if same_name[0]['external_code'].get(rec):
                        _logger.info(msg='External Code for Hotel ' + same_name[0]['name'] + ' for vendor ' + rec +
                                          ': ' + same_name[0]['external_code'][rec] + ' Replace to: ' +
                                         hotel_fmt['external_code'][rec]
                                     )
                    same_name[0]['external_code'].update({rec: str(hotel_fmt['external_code'][rec])})
                same_name[0]['images'] += hotel_fmt['images']
                if len(same_name[0]['facilities']) < len(hotel_fmt['facilities']):
                    same_name[0]['facilities'] = hotel_fmt['facilities']
            else:
                # create baru di memory
                master_cache_content.append(hotel_fmt)

        # Remove Record dari data slave
        file = open('/var/log/cache_hotel/cache_hotel_' + str(slave_index) + '.txt', 'w')
        file.write(json.dumps([]))
        file.close()
        # Write Record ke data master
        file = open('/var/log/cache_hotel/cache_hotel_' + str(master_index) + '.txt', 'w')
        file.write(json.dumps(master_cache_content))
        file.close()
        # Tambah ke alias name
        return True

    # ====================== Activity get City only ============================================
    def mapping_be_my_guest(self):
        vendor_city_ids = glob.glob("/var/log/tour_travel/bemyguest_master_data/*.json")
        need_to_add = []
        for rec1 in vendor_city_ids:
            _logger.info('Open File ' + rec1)
            with open(rec1, 'r') as f:
                vendor_hotel_objs = f.read()
            f.close()

            for rec in json.loads(vendor_hotel_objs)['product_detail']:
                for rec1 in rec['product']['countries']:
                    for rec2 in rec['product']['cities']:
                        new_rec = [rec1, rec2]
                        if new_rec not in need_to_add:
                            need_to_add.append(new_rec)

        with open('/var/log/tour_travel/bemyguest_master_data/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add)
        csvFile.close()
        return True

    # ====================== Correction after mapping ============================================
    def get_other_facility_name(self):
        return True

    def set_other_facility_name(self):
        return True
    # ====================== Cache Hotel to Gateway ==============================================
    @api.multi
    def prepare_gateway_cache(self):
        API_CN_HOTEL.signin()
        file_number = 1
        while file_number:
            try:
                name = "cache_hotel_" + str(file_number-1) + ".txt"
                # file = open("/var/log/cache_hotel/" + name, 'r')
                file = open("/var/log/tour_travel/cache_hotel/" + name, 'r')
                content = file.read()
                file.close()
                API_CN_HOTEL.send_request('create_hotel_file', {'name': name, 'content': content})
            except:
                API_CN_HOTEL.send_request('prepare_gateway_cache', {
                    'hotel_ids': [],
                    'city_ids': [],
                    'country_ids': self.env['test.search'].prepare_countries(self.env['res.country'].sudo().search([])),
                    'landmark_ids': [],
                    'meal_type_ids': self.env['tt.meal.type'].render_cache(),
                    'meal_category_ids': self.env['tt.meal.category'].render_cache(),
                })
                break
            file_number += 1

    # ====================== Cache Hotel edo ke odoo ==============================================
    def compare_hotel_jupiter(self, curr_hotel, new_hotel):
        curr_hotel['external_code'].update(new_hotel['external_code'])
        curr_hotel['name'] = len(curr_hotel['name']) > len(new_hotel['name']) and curr_hotel['name'] or new_hotel['name']
        curr_hotel['location']['address'] = len(curr_hotel['location']['address']) > len(new_hotel['location']['address'])\
                                            and curr_hotel['location']['address'] or new_hotel['location']['address']
        return curr_hotel

    def create_odoo_by_jupiter(self, url):
        return True

    def jupiter_reader(self):
        need_to_add = [['No', 'Country', 'City', 'No Similar', 'To Merge', 'Total']]
        i = 0
        hotel_id = 0
        for path, subdir, files in os.walk('/var/log/tour_travel/jupiter_master/'):
            for country in subdir:
                # if country == '00Result00':
                if country != 'Indonesia': #testing indon only
                    continue
                try:
                    path = '/var/log/tour_travel/jupiter_master/00Result00/' + country
                    os.mkdir(path)
                except:
                    pass
                for path1, subdir1, files1 in os.walk('/var/log/tour_travel/jupiter_master/' + country):
                    for city in subdir1:
                        i += 1
                        a = []
                        current_hotel_objs = []
                        no_similar = 0
                        to_merge = 0

                        if os.path.isfile('/var/log/tour_travel/jupiter_master/' + country + '/' + city + '/rodex_hotel_result.csv'):
                            with open('/var/log/tour_travel/jupiter_master/' + country + '/' + city + '/rodex_hotel_result.csv', 'r') as f:
                                rendered_city_ids = csv.reader(f)
                                is_header = 0
                                # providers = []
                                for rec in rendered_city_ids:
                                    if is_header == 0:
                                        is_header = rec[2:7]
                                        continue
                                    vendor_list = 0
                                    idx = 0
                                    current_hotel_obj = {}
                                    for code in rec[2:7]:
                                        if str(code) != '0':
                                            vendor_list += 1
                                            # providers.append([is_header[idx].lower(), code])

                                            # Find Object
                                            with open(
                                                    '/var/log/cache_hotel/jupiter_master/' + country + '/' + city + '/' +
                                                    is_header[idx].lower() + '_' + city + '.csv', 'r') as f_hotel:
                                                file_hotel_data = csv.reader(f_hotel)
                                                for rec1 in file_hotel_data:
                                                    if rec1[0] == code:
                                                        hotel_id += 1
                                                        # Fungsi Mapping dari csv nya edo ke template rodextrip
                                                        hotel_obj_fmt = self.formating_homas_jupiter(hotel_id, rec1, is_header[idx].lower())
                                                        if not current_hotel_obj:
                                                            current_hotel_obj = hotel_obj_fmt
                                                        else:
                                                            current_hotel_obj = self.compare_hotel_jupiter(current_hotel_obj, hotel_obj_fmt)
                                                        break
                                            f_hotel.close()

                                        idx += 1
                                    if vendor_list > 1:
                                        to_merge += 1
                                    else:
                                        no_similar += 1
                                    a.append(rec)
                                    current_hotel_objs.append(current_hotel_obj)
                                    # G bsa ambil facility + image dari tempate edo
                                    # Flow buat ambil data per city kedata vendor
                            f.close()
                            need_to_add.append([i, country, city, no_similar, to_merge, len(a)])
                            _logger.info('Open {} - {} Success, get {} record(s)'.format(country, city, len(a)))
                        else:
                            for prov in ['knb', 'dida']:
                                if os.path.isfile('/var/log/tour_travel/jupiter_master/' + country + '/' + city + '/'+ prov +'_' + city + '.csv'):
                                    with open('/var/log/tour_travel/jupiter_master/' + country + '/' + city + '/'+ prov +'_' + city + '.csv','r') as f:
                                        hotel_ids = csv.reader(f)
                                        is_header = 0
                                        for rec in hotel_ids:
                                            if is_header == 0:
                                                is_header = 1
                                                continue
                                            hotel_obj_fmt = self.formating_homas_jupiter(hotel_id, rec, prov)
                                            no_similar += 1
                                            a.append(rec)
                                            current_hotel_objs.append(hotel_obj_fmt)
                                            # G bsa ambil facility + image dari tempate edo
                                            # Flow buat ambil data per city kedata vendor
                                    f.close()
                                    need_to_add.append([i, country, city, no_similar, to_merge, len(a)])
                                    _logger.info('Open {} - {} Success, get {} record(s)'.format(country, city, len(a)))

                        file = open(path + '/' + city + '.json', 'w')
                        file.write(json.dumps(current_hotel_objs))
                        file.close()

        # Write Result
        _logger.info('Write in XD')
        with open('/var/log/tour_travel/jupiter_master/00Result00/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add)
        csvFile.close()
        return True

    # ====================== Cache Hotel ke Backend(jadi record di db backend) ====================
    def move_from_cache_to_odoo(self):
        hotel_per_cities = glob.glob("/var/log/tour_travel/cache_hotel/*.txt")
        hotel_per_cities.sort()
        for hotel_per_city in hotel_per_cities[0:10]:
            _logger.info('Open File ' + hotel_per_city)
            with open(hotel_per_city, 'r') as f:
                hotel_objs = f.read()
                hotel_objs = json.loads(hotel_objs)
            f.close()

            _logger.info('Creating ' + str(len(hotel_objs)) + ' Hotel(s)')
            for hotel_obj in hotel_objs:
                create_hotel_id = self.create_hotel(hotel_obj, hotel_per_city.split('/')[-1][12:-4])

    def remove_data_created_from_cache(self):
        for rec in self.env['tt.hotel'].search([('id', '>', 5)]):
            for rec1 in rec.provider_hotel_ids:
                rec1.sudo().unlink()
            rec.facility_ids = [(6,0,[])]
            for rec1 in rec.image_ids:
                rec1.sudo().unlink()
            rec.sudo().unlink()

    # Temporary
    def edit_city_name(self):
        filename = '/var/log/tour_travel/autocomplete_cache.json'
        with open(filename) as f:
            data = json.load(f)
            for rec in data['city_ids']:
                if rec['name'] == 'Surakarta':
                    rec['name'] = 'Solo'
        f.close()

        file = open(filename, 'w')
        file.write(json.dumps(data))
        file.close()

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
    def v2_collect_by_system(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',')  # 'knb',dida,webbeds
        for rec in provider:
            def_name = 'v2_collect_by_system_%s' % rec
            if hasattr(self, def_name):
                return getattr(self, def_name)()
            else:
                _logger.error(msg='No function Collect by CSV for this provider %s' % rec)
        return False

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    # Todo: Perlu catat source data ne
    def v2_collect_by_human(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',') #'knb',dida,webbeds
        for rec in provider:
            def_name = 'v2_collect_by_human_%s' % rec
            if hasattr(self, def_name):
                return getattr(self, def_name)()
            else:
                _logger.error(msg='No function Collect by CSV for this provider %s' % rec)
        return False

    def v2_collect_by_human_csv(self):
        return False

    # 1c. Get Country Code
    def v2_get_country_code(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',')
        for rec in provider:
            def_name = 'v2_get_country_code_%s' % rec
            if hasattr(self, def_name):
                return getattr(self, def_name)()
            else:
                _logger.error(msg='No function get country code for this provider %s' % rec)
        return False

    # 1d. Get City Code
    def v2_get_city_code(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',') #'knb',dida,webbeds
        for rec in provider:
            def_name = 'v2_get_city_code_%s' % rec
            if hasattr(self, def_name):
                return getattr(self, def_name)()
            else:
                _logger.error(msg='No function get city code for this provider %s' % rec)
        return False

    # 1e. Get Meal Code
    def v2_get_meal_code(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',') #'knb',dida,webbeds
        for rec in provider:
            def_name = 'v2_get_meal_code_%s' % rec
            if hasattr(self, def_name):
                return getattr(self, def_name)()
            else:
                _logger.error(msg='No function get meal code for this provider %s' % rec)
        return False

    # 1f. Get room Code
    def v2_get_room_code(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',')  # 'knb',dida,webbeds
        for rec in provider:
            def_name = 'v2_get_room_code_%s' % rec
            if hasattr(self, def_name):
                return getattr(self, def_name)()
            else:
                _logger.error(msg='No function get meal code for this provider %s' % rec)
        return False

    # 1g. Get Facility Code
    def v2_get_facility_code(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',')  # 'knb',dida,webbeds
        for rec in provider:
            def_name = 'v2_get_facility_code_%s' % rec
            if hasattr(self, def_name):
                return getattr(self, def_name)()
            else:
                _logger.error(msg='No function get Facility code for this provider %s' % rec)
        return False

    # 1h. Get Hotel Image
    def get_hotel_image(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',')  # 'knb',dida,webbeds
        for rec in provider:
            def_name = 'get_hotel_image_%s' % rec
            if hasattr(self, def_name):
                return getattr(self, def_name)()
            else:
                _logger.error(msg='No function get Hotel Image for this provider %s' % rec)
        return False

    # 2. Merge
    # Compiller: Master
    # Notes: Compare Hotel lalu simpan hasil Komparasi
    # Notes: Compare hanya 1 Vendor dengan data Master
    # Todo: masukan inputan tingkat kepercayaan untuk langsung validasi
    def v2_merge_record(self):
        # Read CSV CITY
        provider_list = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',')
        params = self.env['ir.config_parameter'].sudo().get_param('hotel.merge.provider')
        if params == json.dumps(provider_list):
            params = self.env['ir.config_parameter'].sudo().get_param('hotel.city.rendered.list')
            rendered_city = json.loads(params)
        else:
            self.env['ir.config_parameter'].sudo().set_param('hotel.merge.provider', json.dumps(provider_list))
            rendered_city = []
        len_rendered = len(rendered_city)
        target_city_index = int(len_rendered)
        hotel_id = 0

        import glob
        for master_provider in provider_list:
            base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
            base_url = base_cache_directory + master_provider + "/"

            looped_country = os.walk(base_url)
            for country in os.walk(base_url):
                if isinstance(country, tuple):
                    looped_country = country[1]
                    break
                else:
                    break

            for country in looped_country:
                country_str = country

                # if country_str == 'Turks And Caicos Islands':
                #     country_str = country_str

                # if country_str != 'ID':
                #     _logger.info('Skiping Data For Country: ' + country_str + '. Not in Search range')
                #     continue
                city_ids = glob.glob(base_url + country_str + "/*.json")
                for target_city in city_ids:
                    city_name = target_city[len(base_url) + len(country_str) + 1:-5]
                    if len(country_str.split('/')) == 2:
                        state_name = country_str.split('/')[-1]
                        country_name = country_str.split('/')[0]
                    else:
                        state_name = ''
                        country_name = country_str
                    if city_name.lower() in rendered_city:
                        _logger.info('Skipping Already Render City ' + city_name.lower() + '; ' + country_name)
                        continue
                    # Versi 2020/12 hotel di hubungkan dengan City langsung
                    # city_obj = self.env['res.city'].find_city_by_name(city_name, limit=1)
                    # if not city_obj:
                    #     try: #Coba catat user siapa yg buat jika user g pnya hak akses apa perlu dikasih error?
                    #         city_obj = self.env['res.city'].create({'name': city_name, 'country_id':self.env['res.country'].search([('name','=ilike','other')], limit=1)[0].id})
                    #     except: #sementara di bypass tnpa notif dan di catat create by admin
                    #         city_obj = self.env['res.city'].sudo().create({'name': city_name, 'country_id':self.env['res.country'].search([('name','=ilike','other')], limit=1)[0].id})

                    # Versi 2021/01 hotel di hubungkan dengan tt.hotel.destination
                    is_exact, destination_obj = self.env['tt.hotel.destination'].find_similar_obj({
                        'id': False,
                        'name': city_name,
                        'city_str': city_name,
                        'state_str': state_name if state_name != country_name else '',
                        'country_str': country_name,
                    }, force_create=True)
                    city_obj = destination_obj.city_id
                    country_obj = destination_obj.country_id
                    city_id = city_obj and city_obj.id or self.env['res.city'].find_city_by_name(city_name, 1)
                    self.file_log_write(str(target_city_index + 1) + '. Start Render: ' + city_name + '; ' + country_name)
                    searched_city_names = [city_name, ]
                    searched_city_names += [rec.name for rec in city_obj.other_name_ids.filtered(lambda x: x.name not in city_name)]

                    # Matikan Temp untuk speed up
                    # searched_city_ids = self.compute_related_city(city_obj, city_name)

                    # Loop All provider untuk setiap city di alias name
                    for searched_city_name in searched_city_names:
                        for provider in provider_list:
                            a = 0
                            provider_id = self.env['tt.provider'].search(['|',('alias','=', provider),('code','=', provider)], limit=1).id
                            code_objs = self.env['tt.provider.code'].search([('provider_id', '=', provider_id), ('res_model', '=', 'tt.hotel')])
                            code_ids = [x.code for x in code_objs]
                            try:
                                file_url = base_cache_directory + provider + "/" + country_str + "/" + searched_city_name + ".json"
                                # Loop untuk setiap city cari file yg nama nya sma dengan  city yg dimaksud
                                with open(file_url, 'r') as f2:
                                    file = f2.read()
                                    self.file_log_write('Provider ' + provider + ', for alias name ' + searched_city_name + ': ' + str(len(json.loads(file))))
                                    a += len(json.loads(file))
                                    for hotel in json.loads(file):
                                        hotel_id += 1
                                        # rubah format ke odoo
                                        # if any([x in hotel['name'].lower().split(' ') for x in ['oyo', 'reddoorz', 'airy']]) and 'formerly' not in hotel['name'].lower().split(' '):
                                        #     _logger.info('Skipping OYO ' + hotel['name'])
                                        #     continue
                                        if hotel['id'] in code_ids:
                                        # if self.env['tt.provider.code'].search([('provider_id', '=', provider_id), ('code', '=', hotel['id'])], limit=1).ids:
                                            _logger.info('Skipping ' + hotel['name'])
                                            continue
                                        hotel_fmt = self.formating_homas(hotel, hotel_id, provider, city_id, city_name, destination_obj.id, country_obj.id)

                                        internal_hotel_obj = self.create_or_edit_hotel(hotel_fmt, -1, provider_id)
                                        # if internal_hotel_obj:
                                        #     internal_hotel_obj.advance_find_similar_name_from_database_2()
                                        if hotel_id % 10 == 0:
                                            _logger.info('====== Saving Poin Hotel Raw Data ======')
                                            self.env.cr.commit()
                                f2.close()
                            except Exception as e:
                                self.file_log_write('Error:' + provider + ' in id ' + str(hotel_id) + '; MSG:' + str(e))
                                try:
                                    f2.close()
                                    pass
                                except:
                                    pass

                    _logger.info('Render ' + city_name + ' End')

                    # Simpan di rendered hotel
                    for rec in searched_city_names:
                        # Simpan all alias name juga
                        rendered_city.append(rec.lower())

                    target_city_index += 1

                    self.env['ir.config_parameter'].sudo().set_param('hotel.city.rendered.list', json.dumps(rendered_city))
                    self.env.cr.commit()
        _logger.info('===============================')
        _logger.info('==        RENDER DONE        ==')
        _logger.info('===============================')
        # Reset Parameter jika sdah selesaai
        self.env['ir.config_parameter'].sudo().set_param('hotel.city.rendered.list', json.dumps([]))

    # 2a. Get Hotel Image
    def v2_get_hotel_image(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',')  # 'knb',dida,webbeds
        for rec in provider:
            def_name = 'v2_get_hotel_image_%s' % rec
            if hasattr(self, def_name):
                return getattr(self, def_name)()
            else:
                _logger.error(msg='No function get Hotel Image for this provider %s' % rec)
        return False

    # 2b. Proses Hotel Raw yg blum ada di comparer
    def v2_sent_all_hotel_to_comparer(self):
        # Cari hotel_id yg draft
        err_list = []
        x = 0
        for rec in self.env['tt.hotel'].search([('state','=','draft'),('state','!=',False),('id','>',22774)]): #Test pakai sandton('city_id','=',396925)
            x += 1
            try:
                # Create Comparer ulang sebagai record sja
                comparing_id = self.env['tt.hotel.compare'].create({
                    'hotel_id': rec.id,
                    'comp_hotel_id': False,
                })
                comparing_id.to_merge_hotel()
            except:
                err_list.append(rec.id)
                _logger.info('Error while processing: ' + str(rec.id))
                continue

            if x % 80 == 0:
                _logger.info('Saving Record (v2_sent_all_hotel_to_comparer) to ' + str(x))
                self.env.cr.commit()
        return True

    # 2c. Proses Hotel dari comparer
    def v2_proceeding_hotel_comparer(self):
        # Baca Smua comparer jika ada status draft kasih notif g bisa di proses
        # if self.env['tt.hotel.compare'].search([('state','=','draft')]):
        #     raise UserError('Some Record still in Draft State:')
        # Merge smua yg tobe_merge
        x = 0
        for rec in self.env['tt.hotel.compare'].search([('state', '=', 'tobe_merge')]):
            if rec.comp_hotel_id:
                _logger.info(msg=str(x+1) + '. ' + rec.hotel_id.name + ' => ' + rec.comp_hotel_id.name + ' Score:' + str(rec.score))
            else:
                _logger.info(msg=str(x + 1) + '. ' + rec.hotel_id.name + ' (New)')
            try:
                rec.merge_hotel()
                x += 1
            except:
                # Error disin biasane karena hotel raw tdak ada provider codenya
                # Asumsi jika error disini maka data yg error blum brubah jadi masih tobe_merge g susah tracing nya
                _logger.info(msg='Error Merge: ' + rec.hotel_id.name)
                continue

            if x % 15 == 0:
                _logger.info(msg='=======================================')
                _logger.info(msg='     Writing Comparer to ' + str(x))
                _logger.info(msg='=======================================')
                self.env.cr.commit()
        _logger.info(msg='======================================')
        _logger.info(msg='======================================')
        _logger.info(msg='==     END (2C) Writing Compare     ==')
        _logger.info(msg='======================================')
        _logger.info(msg='======================================')
        return True

    def check_content_length(self, content, dest_name, country_name, idx=200):
        if len(content) % idx == 0:
            _logger.info(msg='Write Partial Render ' + dest_name + ', ' + country_name + ' with '+ str(len(content)) + ' data')

            file = open('/var/log/tour_travel/cache_hotel/cache_hotel_partial_render.txt', 'w')
            file.write(json.dumps(content))
            file.close()
        elif len(content) % 100 == 0:
            _logger.info(msg='Rendering ' + dest_name + ', ' + country_name + ' with ' + str(len(content)) + ' data')
    def uncontent(self):
        file = open('/var/log/tour_travel/cache_hotel/cache_hotel_partial_render.txt', 'w')
        file.write(json.dumps([]))
        file.close()

    # 3. Send Hotel to GW
    # Compiller: Master, Send: GW Rodextrip
    # Notes: Read Data Hotel kumpulkan per City kirim ke GW
    # Todo: Kirimkan juga Meal Type Code yg ada di cache + data yg kita perlukan lain nya
    def v2_prepare_gateway_cache(self):
        # Find prefered City
        idx = 1
        catalog = []
        last_render = int(self.env['ir.config_parameter'].sudo().get_param('last.gw.render.idx'))
        if last_render == 0: #Jika mulai baru
            for destination in self.env['tt.hotel.destination'].search([('active', '=', True)]): #Test pakai south africa ('country_id','=',247)
                # Rename city as File_number // 7an supaya waktu send data kita bisa tau file mana yg hilang klo pakai nama city mesti buka index dulu baru tau klo ada file hilang
                # Loop sngaja dibuat 2x ini tujuan nya buat bikin daftar isi trus kirim ke GW
                daaata = {
                    'index': idx,
                    'id': destination.id,
                    'name': destination.name,
                    'destination_id': destination.id,
                    'destination_name': destination.name,
                    'city_id': '',
                    'city_name': '',
                    'alias': '',
                    'country_id': '',
                    'country_name': '',
                    'country_code': '',
                    'country_phone_code': '',
                }
                city = destination.city_id
                if city:
                    daaata.update({
                        'city_id': city.id,
                        'city_name': city.name,
                        'alias': city and ','.join([rec.name for rec in city.other_name_ids]) or '',
                        'name': city.get_full_name()
                    })
                country = destination.country_id and city.country_id
                if country:
                    daaata.update({
                        'country_id': country.id,
                        'country_name': country.name,
                        'country_code': country.code,
                        'country_phone_code': country.phone_code,
                    })
                catalog.append(daaata)
                idx += 1
            # API_CN_HOTEL.send_request('send_catalog', json.dumps(catalog))
            # Test Only: Langsung Write as DB
            file = open('/var/log/tour_travel/cache_hotel/catalog.txt', 'w')
            file.write(json.dumps(catalog))
            file.close()
        else:  #Jika Error atau last blum selesai
            f2 = open('/var/log/tour_travel/cache_hotel/catalog.txt', 'r')
            f2 = f2.read()
            catalog = json.loads(f2)

        catalog.sort(key=lambda k: k['index'])
        for city in catalog:
            if last_render != 0 and int(city['index']) <= int(last_render):
                _logger.info(msg=str(city['index']) +'. Skip hotel Destination: ' + city.get('destination_name') or '-' + ', Country: ' + city.get('country_name') or '-')
                continue
            _logger.info(msg='Render hotel Destination: ' + city.get('destination_name') + ', Country: ' + city.get('country_name') or '-')
            f2 = open('/var/log/tour_travel/cache_hotel/cache_hotel_partial_render.txt', 'r')
            f2 = f2.read()
            content = json.loads(f2)

            if not content:
                # Search all Mapped Data from hotel.master
                for hotel in self.env['tt.hotel.master'].search([('destination_id','=',city['destination_id'])]):
                    content.append(hotel.fmt_read())
                    self.check_content_length(content, city['destination_name'], city['country_name'])

                # Rubah ke format JSON
                # Save as 1 File and send to GW
                # API_CN_HOTEL.send_request('create_hotel_file', {'name': 'cache_hotel_' + str(city['index']), 'content': json.dumps(content)})

                # Urgent all DIDA di render
                for hotel in self.env['tt.hotel'].search([('destination_id','=',city['destination_id']),('state','=','draft'),('compare_ids','=',False),('provider','=','Dida Hotel Vendor')]):
                    content.append(hotel.fmt_read())
                    self.check_content_length(content, city['destination_name'], city['country_name'])
            else:
                _logger.info(msg='Content available continuing with ' + str(len(content)) + ' data for ' + city['destination_name'])
                content_idx = [x['id'] for x in content]
                if len(self.env['tt.hotel.master'].search([('destination_id', '=', city['destination_id'])]).ids) > len(content_idx):
                    for hotel in self.env['tt.hotel.master'].search([('destination_id', '=', city['destination_id'])]):
                        hotel_id = hotel.internal_code or hotel.id
                        if hotel_id not in content_idx:
                            content.append(hotel.fmt_read())
                            self.check_content_length(content, city['destination_name'], city['country_name'])
                
            self.uncontent()
                # Test Only: Langsung Write as DB
            try:
                file = open('/var/log/tour_travel/cache_hotel/cache_hotel_' + str(city['index']) + '.txt', 'w')
                file.write(json.dumps(content))
                file.close()
                _logger.info(msg=str(city['index']) +'. Create hotel file ' + city['destination_name'] + ', ' + city['country_name'] + ' with ' + str(len(content)) + ' Hotel(s) Done')

                # Last Render ID Here:
                self.env['ir.config_parameter'].sudo().set_param('last.gw.render.idx', city['index'])
                self.env.cr.commit()
            except Exception as e:
                _logger.error(msg='Create hotel file Error')
                continue
        self.env['ir.config_parameter'].sudo().set_param('last.gw.render.idx', 0)
        _logger.info(msg='============== Render Done ==============')
        return True

    # 3a. Partial Update Data
    # Notes: Part ini di panggil untuk revisi data Cache pada suatu kota
    # Contoh: Update nama hotel, adding new info kyak facility ataupun Gmbar
    def v3_partial_send_cache(self):
        f2 = open('/var/log/tour_travel/cache_hotel/catalog.txt', 'r')
        f2 = f2.read()
        catalog = json.loads(f2)

        try:
            file = open('/var/log/tour_travel/cache_hotel/cache_hotel_partial.txt', 'r')
            content = file.read()
            content = json.loads(content)
            cache_data_id = [x['id'] for x in content]
            file.close()
        except:
            content = []
            cache_data_id = []

        _logger.info(msg='============== Render Start ==============')
        catalog.sort(key=lambda k: k['index'])
        rewrite_city = self.env['ir.config_parameter'].sudo().get_param('rewrite.city')
        for rewrite_city_name in rewrite_city.split(','):
            for city in catalog:
                if city['destination_name'].lower() != rewrite_city_name:
                # if city['city_name'].lower() not in rewrite_city.split(','): #Old Version
                    continue
                # content = []
                # Search all Mapped Data from hotel.master

                render_idx = 0
                # Prt #1 Strt
                for hotel in self.env['tt.hotel.master'].search(['|',('city_id','=',city['city_id']),('destination_id','=',city['destination_id'])]):
                    if hotel.internal_code in cache_data_id:
                        continue
                    hotel_fmt = hotel.fmt_read(city_idx=city['index'])
                # Prt #1 End
                # for hotel in self.env['tt.hotel'].search([('city_id','=',city['city_id'])]):  #Old Version
                # Prt #2 Strt
                # for hotel in self.env['tt.hotel'].search([('destination_id','=',city['destination_id']),('provider','=','Hotelinx')]):
                #     if 'dmhtx_' + str(hotel.id) in cache_data_id:
                #         _logger.info(msg='Skip '+ hotel.name)
                #         continue
                #     hotel_fmt = hotel.fmt_read(city_idx=city['index'])
                #     hotel_fmt.update({'id': 'dmhtx_' + hotel_fmt['id'], })
                # Prt #2 End
                    content.append(hotel_fmt)
                    _logger.info(msg='Adding Hotel ' + hotel.name)

                    render_idx += 1
                    if render_idx % 100 == 0:
                        _logger.info(msg='============ Save Cache ============')
                        file = open('/var/log/tour_travel/cache_hotel/cache_hotel_partial.txt', 'w')
                        file.write(json.dumps(content))
                        file.close()
                try:
                    # with open('/var/log/tour_travel/cache_hotel/cache_hotel_' + str(city['index']) + '.txt', 'r') as f2:
                    #     record = f2.read()
                    #     old_rec = json.loads(record)
                    # content += old_rec

                    file = open('/var/log/tour_travel/cache_hotel/cache_hotel_partial.txt', 'w')
                    file.write(json.dumps([]))
                    file.close()
                    _logger.info(msg='=== Clear Partial Done ===')

                    file = open('/var/log/tour_travel/cache_hotel/cache_hotel_' + str(city['index']) + '.txt', 'w')
                    file.write(json.dumps(content))
                    file.close()
                    _logger.info(msg=str(city['index']) + '. ReWrite hotel file ' + city['destination_name'] + ', ' + city['country_name'] + ' with ' + str(len(content)) + ' Hotel(s) With File Index: '+ str(city['index']) +' Done')
                    # _logger.info(msg=str(city['index']) + '. ReWrite hotel file ' + city['city_name'] + ' with ' + str(len(content)) + ' Hotel(s) Done')  #Old Version
                except Exception as e:
                    _logger.error(msg=str(city['index']) + '. ReWrite hotel file ' + city['destination_name'] + ', ' + city['country_name'] + ' Error Render')
                    continue
                break
        _logger.info(msg='============== Render Done ==============')
        return True

    # 3c. Update meal_type Data
    def v3_partial_send_cache_meal_type(self):
        file = open('/var/log/tour_travel/autocomplete_hotel/meal_cache.json', 'w')
        file.write(json.dumps({
            'meal_type_ids': self.env['tt.meal.type'].render_cache(),
            'meal_category_ids': self.env['tt.meal.category'].render_cache(),
        }))
        file.close()

    def prepare_gateway_cache(self, new_cache_dict):
        return True

    # 4. Render AutoComplete
    # Notes: Render City + Auto complete
    # Notes: Kirim Auto Complete ke channel / B2B ne
    # Todo: Data city sementara menggunakan data city master
    @api.multi
    def v2_render_autocomplete(self):
        provider_list = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',')
        new_cache_dict = {
            'hotel_ids': [],
            'city_ids': self.env['test.search'].render_cache_city_for_gw(providers=provider_list),
            # 'city_ids': [],
            'country_ids': self.env['test.search'].prepare_countries(self.env['res.country'].sudo().search([])),
            'landmark_ids': [],
            'meal_type_ids': self.env['tt.meal.type'].render_cache(),
            'meal_category_ids': self.env['tt.meal.category'].render_cache(),
        }
        # Update ke master nya
        if int(self.env['ir.config_parameter'].sudo().get_param('last.gw.render.idx')) == 0:
            API_CN_HOTEL.signin()
            API_CN_HOTEL.send_request('prepare_gateway_cache', new_cache_dict)

        _logger.info('Render Cache Done ' + str(len(new_cache_dict['city_ids'])) + ' City(s), ' + str(len(new_cache_dict['country_ids'])) + ' Countries,')
        # Update ke BTBO2 dkk / Child / subscribers
        _logger.info('Sending to Child')
        vals = {
            'provider_type': 'hotel',
            'action': 'prepare_gateway_cache',
            'data': new_cache_dict,
        }
        # self.env['tt.api.webhook.data'].notify_subscriber(vals)
        _logger.info('Send to Child Done')

    # 5. Get New Hotel from Gateway
    # Notes: Waktu proses search bisa jadi dapat data yg tidak lengkap atau tidak ada dalam cache
    # Notes: Simpan data ne as Raw File
    # Todo: Perlu catat source data ne waktu kita create raw dari mana
    # Todo: Pertimbangkan saat new hotel pnya meal type code & facility code yg tidak terdaftar
    # Notes: Control datane disini biar next search dia tidak kosongan / gagal di tampilin
    def v2_receive_data_from_gateway(self):
        # render_city = 'Surabaya'
        render_city = self.env['ir.config_parameter'].sudo().get_param('rewrite.city')
        render_city = render_city.split(',')[0]
        render_city = render_city.capitalize()
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        city_file_url = base_cache_directory + 'from_cache/'+ render_city +'.json'
        f2 = open(city_file_url, 'r')
        f2 = f2.read()
        catalog = json.loads(f2)

        for rec in catalog:
            city_name = rec['location']['city']

            is_exact, destination_obj = self.env['tt.hotel.destination'].find_similar_obj({
                'id': False,
                'name': False,
                'city_str': city_name,
                'state_str': rec['location']['state'],
                'country_str': rec['location']['country'],
            })
            city_obj = destination_obj.city_id
            city_id = city_obj and city_obj.id or self.env['res.city'].find_city_by_name(city_name, 1)

            provider = list(rec['external_code'].keys())[0]
            hotel_id = rec['external_code'][provider]

            hotel_fmt = self.formating_homas(rec, hotel_id, provider, city_id, city_name, destination_obj.id)
            hotel_fmt['location']['address'] = rec['location']['address']
            self.create_or_edit_hotel(hotel_fmt, -1)
        self.file_log_write('Read and Save Record '+ render_city +' Done')
        return True

    # Tgl 22 Desember 2020:
    # Buat fungsi temporary untuk baca all data dari 1 table google lalu simpan ke odoo
    # target table: meta_location
    # Kriteria khusus: type="CO => Country, RE => State, CI => City", in_location = Parent_id nya
    def temp_func(self):
        query = 'SELECT * FROM meta_location WHERE type = '
        self.env.cr.execute(query + "'CO' order by id")
        country_dict = {}
        for rec in self.env.cr.fetchall():
            # Find Exist Country using Country Code
            country_obj = self.env['res.country'].search([('code','=', rec[7])], limit=1)
            if country_obj:
                country_dict[str(rec[0])] = [country_obj.name, country_obj.id]
            else:
                country_dict[str(rec[0])] = [country_obj.name, country_obj.id]

        state_dict = {}
        self.env.cr.execute(query + "'RE' order by id")
        for rec in self.env.cr.fetchall():
            state_obj = self.env['res.country.state'].create({
                'name': rec[2],
                'code': rec[1],
                'country_id': country_dict[str(rec[4])][1],
            })
            state_dict[str(rec[0])] = [state_obj.name, state_obj.id, state_obj.country_id.id]

        self.env.cr.execute(query + "'CI' order by id")
        for rec in self.env.cr.fetchall():
            try:
                if state_dict.get(str(rec[4])):
                    state_data = state_dict[str(rec[4])]
                else:
                    state_data = country_dict[str(rec[4])] # No State for this City
                self.env['res.city'].create({
                    'name': rec[2],
                    'code': rec[1],
                    'state_id': len(state_data) > 2 and state_data[1] or False,
                    'country_id': len(state_data) > 2 and state_data[2] or state_data[1],
                    'latitude': rec[5],
                    'longitude': rec[6],
                })
            except:
                self.env['res.city'].create({
                    'name': rec[2],
                    'code': rec[1],
                    'state_id': len(state_data) > 2 and state_data[1] or False,
                    'country_id': len(state_data) > 2 and state_data[2] or state_data[1],
                    'latitude': rec[5],
                    'longitude': rec[6],
                })

    # Fungsi untuk adding dri cache selected vendor ke data hasil prepare gateway
    def v3_adding_gateway_cache_direct(self):
    # def v3_partial_send_cache(self):
        hotel_id = 0
        target_city_index = 0
        new_cache_index = 99000

        f2 = open('/var/log/tour_travel/cache_hotel/catalog.txt', 'r')
        f2 = f2.read()
        catalog = json.loads(f2)
        catalog.sort(key=lambda k: k['index'])

        provider_list = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.provider').split(',')
        for master_provider in provider_list:
            base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
            base_url = base_cache_directory + master_provider + "/"

            looped_country = os.walk(base_url)
            for country in os.walk(base_url):
                if isinstance(country, tuple):
                    looped_country = country[1]
                    break
                else:
                    break

            for country in looped_country:
                country_str = country

                city_ids = glob.glob(base_url + country_str + "/*.json")
                for target_city in city_ids:
                    city_name = target_city[len(base_url) + len(country_str) + 1:-5]
                    if len(country_str.split('/')) == 2:
                        state_name = country_str.split('/')[-1]
                        country_name = country_str.split('/')[0]
                    else:
                        state_name = ''
                        country_name = country_str

                    searched_city_name = city_name
                    catalog_index = 0
                    catalog_codes = {}
                    catalog_value = []
                    for city in catalog:
                        if city['destination_name'].lower() == searched_city_name.lower():
                            catalog_index = city['index']
                            f2 = open('/var/log/tour_travel/cache_hotel/cache_hotel_' + str(catalog_index) + '.txt','r')
                            f2 = f2.read()
                            f3 = json.loads(f2)

                            catalog_codes = {}
                            catalog_value = f3
                            for f2_data in f3:
                                for f2_data_key in f2_data['external_code'].keys():
                                    if not catalog_codes.get(f2_data_key):
                                        catalog_codes[f2_data_key] = []
                                    catalog_codes[f2_data_key].append(f2_data['external_code'][f2_data_key])
                            break
                    if not catalog_index:
                        new_cache_index += 1
                        catalog_index = new_cache_index

                    for provider in provider_list:
                        a = 0
                        try:
                            file_url = base_cache_directory + provider + "/" + country_str + "/" + searched_city_name + ".json"
                            # Loop untuk setiap city cari file yg nama nya sma dengan  city yg dimaksud
                            with open(file_url, 'r') as f2:
                                file = f2.read()
                                self.file_log_write('Provider ' + provider + ', for alias name ' + searched_city_name + ': ' + str(len(json.loads(file))))
                                a += len(json.loads(file))
                                for hotel in json.loads(file):
                                    hotel_id += 1
                                    # rubah format ke odoo
                                    # if any([x in hotel['name'].lower().split(' ') for x in ['oyo', 'reddoorz', 'airy']]):
                                    #     _logger.info('Skipping ' + hotel['name'])
                                    #     continue
                                    hotel_fmt = self.formating_homas(hotel, hotel_id, provider, 0, city_name, 0)
                                    ext_code = list(hotel_fmt['external_code'].keys())[0]
                                    if hotel_fmt['external_code'][ext_code] not in catalog_codes.get(ext_code) or []:
                                        _logger.info(msg='Adding ' + str(hotel_fmt['name']) + ' with code ' + str(hotel_fmt['external_code'][ext_code]) + ' From ' + ext_code)
                                        catalog_value.append(hotel_fmt)
                                    # else:
                                    #     _logger.info(msg='Removing ' + str(hotel_fmt['name']) + ' with code ' + str(hotel_fmt['external_code'][ext_code]) + ' Vendor: ' + ext_code)
                            f2.close()

                            # Proses adding dta direct ke cache
                            # 1. Cri apa dest ada di cache
                            #    a. Jika ada add di file tsb
                            #    b. Jika tidak create / cek new file
                            # 2. Loop untuk cek apa external id untuk hotel yg mau kta add sdah ada di cache
                        except Exception as e:
                            self.file_log_write('Error:' + provider + ' in id ' + str(hotel_id) + '; MSG:' + str(e))
                            try:
                                f2.close()
                                pass
                            except:
                                pass

                    file = open('/var/log/tour_travel/cache_hotel/cache_hotel_' + str(catalog_index) + '.txt', 'w')
                    file.write(json.dumps(catalog_value))
                    file.close()

                    _logger.info('Render ' + city_name + ' End')
                    target_city_index += 1
        return True

    # Button "3b. Hotel Mapped for Vendor"
    # Render Hotel Code for some vendor
    def v3_render_hotel_code(self):
        obj_no = 1
        prov_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_miki').id
        csv_data = []
        csv_data.append(['No','provider_name','provider_code','master_name','master_code','master_address','master_city','master_country'])
        for rec in self.env['tt.provider.code'].search([('res_model','=','tt.hotel'),('provider_id','=',prov_id)]):
            hotel_raw_obj = self.browse(rec.res_id)
            for comp_obj in hotel_raw_obj.compare_ids:
                if comp_obj.state in ['merge']:
                    sim_obj = comp_obj.similar_id
                    csv_data.append([obj_no, rec.name, rec.code, sim_obj.name, sim_obj.internal_code, sim_obj.address, sim_obj.destination_id.name , sim_obj.country_id.name])
                    obj_no += 1
                    break

        with open('/var/log/tour_travel/autocomplete_hotel/hotel_code_for_vendor.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(csv_data)
        csvFile.close()

        return csv_data

    def get_xml_data(self, xml_dict, xml_list, is_list=False):
        if not isinstance(xml_list, list):
            xml_list = [xml_list]
        data = xml_dict
        for key in xml_list:
            if not data or not data.get(key):
                data = ''
                break
            data = data[key]
        if not data and is_list:
            data = []
        elif is_list and not isinstance(data, list):
            data = [data]
        return data
