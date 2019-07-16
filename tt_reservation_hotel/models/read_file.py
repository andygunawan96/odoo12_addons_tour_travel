from odoo import api, fields, models, _
import json
import logging
from .ApiConnector_Hotel import ApiConnectorHotels

_logger = logging.getLogger(__name__)
API_CN_HOTEL = ApiConnectorHotels()


class HotelInformation(models.Model):
    _inherit = 'tt.hotel'

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
                                    'city_id': hpc_id and hpc_id.city_id.id or 0,
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
                            city_id = self.env['res.city'].search([('name','=',rec['name'])], limit=1)
                            if not city_id:
                                city_id = self.env['res.city'].search([('name', 'ilike', rec['name'])], limit=1)
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
                        city_id = self.env['res.city'].search([('name', '=', obj['name']['content'])], limit=1)
                        vals.update({'city_id': city_id and city_id[0].id or False})

                    elif obj.get('name') and search_req['type'] == 'hotel':
                        city_id = self.env['res.city'].search([('name', 'ilike', obj['city']['content'])], limit=1)
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
                            'city_id': city_id and city_id[0].id or False
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

    # Quantum Get Hotel By City
    def get_record_by_api2(self):
        api_context = {
            'co_uid': self.env.user.id
        }

        provider_id = self.env['res.partner'].search(
            [('is_master_vendor', '=', True), ('provider_code', '=', 'quantum')], limit=1)
        for rec in self.env['provider.code'].search([('city_id', '!=', False),('provider_id', '=', provider_id.id),('id', '>=', 500659)]):
            search_req = {
                'provider': 'quantum',
                'type': 'city',
                'limit': '0',
                'offset': '0',
                'codes': rec.code,
            }

            res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
            if res['error_code'] != 0:
                raise ('Error')
            else:
                for obj in res.get('response'):
                    if obj.get('code'):
                        city_id = rec.city_id
                        value = {
                            'name': obj.get('basicinfo') and obj.get('basicinfo').get('name') or '',
                            'street': obj.get('addressinfo') and obj['addressinfo'].get('address1') or '',
                            'description': obj.get('locationinfo') and 'Raildistance: ' +
                                           obj['locationinfo'].get('raildistance', ' ') + '; Airport Distance: ' +
                                           obj['locationinfo'].get('airportdistance', ' ') or '',
                            'email': obj.get('contactinfo') and obj.get('contactinfo').get('email') or '',
                            'images': [(6, 0, self.rec_to_images(obj.get('images')))],
                            'phone': obj.get('contactinfo') and obj.get('contactinfo').get('telephonenumber1') or '',
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
                            'city_id': city_id and city_id[0].id or False
                        }
                        hotel_id = self.env['tt.hotel'].create(value)
                        self.env['provider.code'].create({
                            'name': hotel_id.name,
                            'hotel_id': hotel_id.id,
                            'code': obj.get('code'),
                            'provider_id': provider_id[0].id,
                        })
                        self.env.cr.commit()

        return True

    # Miki Travel
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
        provider_id = self.env['res.partner'].search([('provider_code', '=', 'miki')], limit=1)
        res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        if res['error_code'] != 0:
            raise ('Error')
        else:
            for obj in res.get('response'):
                if obj.get('code'):
                    city_id = res.city_id
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
                        'city_id': city_id and city_id[0].id or False
                    }
                    hotel_id = self.env['tt.hotel'].create(value)
                    self.env['provider.code'].create({
                        'name': hotel_id.name,
                        'hotel_id': hotel_id.id,
                        'code': obj.get('code'),
                        'provider_id': provider_id[0].id,
                    })
                    self.env.cr.commit()

        return True

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
                                'city_id': city_id,
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
                city_id = self.env['res.city'].search([('name', 'ilike', city['name'])], limit=1)
                if city_id:
                    vals.update({'city_id': city_id and city_id[0].id or False})
                    city_ids.append({
                        'code': city['code'],
                        'city_id': city_id[0].id,
                        'country_code': country['code']
                    })
                self.env['provider.code'].create(vals)
                self.env.cr.commit()

        # if not city_ids:
        #     temp_data = self.env['provider.code'].search([('provider_id', '=', provider_id[0].id), ('city_id', '!=', False)])
        #     for rec in temp_data:
        #         country_code_obj = rec.city_id.country_id and rec.city_id.country_id.provider_city_ids.filtered(lambda x: x.provider_id.id == provider_id[0].id) or False
        #         city_ids.append({
        #             'code': rec.code,
        #             'city_id': rec.city_id.id,
        #             'country_code': country_code_obj and country_code_obj[0].id or False
        #         })
        # for rec in city_ids:
        #     if rec['code'] and rec['country_code']:
        #         search_req = {
        #             'provider': 'itank',
        #             'type': 'hotel',
        #             'limit': '20',
        #             'offset': '1',
        #             'codes': str(rec['code']) + '~' + str(rec['country_code']),
        #         }
        #         res = API_CN_HOTEL.get_record_by_api(search_req, api_context)
        #         for hotel_rec in res['response']:
        #             temp_data = self.env['provider.code'].search(
        #                 [('provider_id', '=', provider_id[0].id), ('code', '=', hotel_rec['code']), ('hotel_id', '!=', False)])
        #             # Rec already exist
        #             if temp_data:
        #                 temp_data[0].hotel_id.update({
        #                     'star': hotel['star'],
        #                     'email': hotel['email'],
        #                     'phone': hotel['phone'],
        #                     'fax': hotel['fax'],
        #                     'url': hotel['url'],
        #                     'address': hotel['address'],
        #                     'lat': hotel['lat'],
        #                     'long': hotel['long'],
        #                     'zip': hotel['zip'],
        #                     'hotel_desc': hotel['hotel_desc'],
        #                     'hotel_image': hotel['hotel_image']
        #                 })
        #             else:
        #                 # Create Hotel
        #                 hotel_id = self.env['tt.hotel'].sudo().create({
        #                     'star': hotel['star'],
        #                     'email': hotel['email'],
        #                     'phone': hotel['phone'],
        #                     'fax': hotel['fax'],
        #                     'url': hotel['url'],
        #                     'address': hotel['address'],
        #                     'lat': hotel['lat'],
        #                     'long': hotel['long'],
        #                     'zip': hotel['zip'],
        #                     'hotel_desc': hotel['hotel_desc'],
        #                     'hotel_image': hotel['hotel_image'],
        #                 })
        #                 # Create Provider Code
        #                 self.env['provider.code'].sudo().create({
        #                     'code': hotel['code'],
        #                     'provider_id': provider_id[0].id,
        #                     'hotel_id': hotel_id.id
        #                 })
        return True

    # Itank Remove
    def remove_itank(self):
        provider_id = self.env['res.partner'].search(
            [('is_master_vendor', '=', True), ('provider_code', '=', 'itank')], limit=1)
        recs = self.env['provider.code'].search([('provider_id', '=', provider_id[0].id)])
        for rec in recs:
            rec.sudo().unlink()
