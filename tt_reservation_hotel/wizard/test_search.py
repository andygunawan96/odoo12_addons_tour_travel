import copy

from odoo import api, fields, models, _
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
from ...tools import util,variables,ERR
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import date, datetime, timedelta
from decimal import Decimal
from odoo.exceptions import UserError
import json
from ...tools.ERR import RequestException
import logging,traceback
_logger = logging.getLogger(__name__)

class TestSearch(models.Model):
    _name = 'test.search'
    _description = 'Test Search Model'

    name = fields.Char('City / Hotel Name', default=' ')
    hotel_id = fields.Many2one('tt.hotel', 'Hotel', related='rate_id.room_info_id.hotel_id')
    room_id = fields.Many2one('tt.room.info', 'Room', related='rate_id.room_info_id')
    line_ids = fields.One2many('test.search.line', 'reservation_id', 'Line')
    line_2_ids = fields.One2many('test.search.line2', 'reservation_id', 'Decr Line')
    rate_id = fields.Many2one('tt.room.rate', 'Room Rate')
    day = fields.Selection([
        (7, 'Sunday'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
    ], 'Day', default=1)
    date_start = fields.Date('Date Start', default=fields.Date.context_today)
    date_end = fields.Date('Date End', default=fields.Date.context_today)
    nights = fields.Integer('Room')
    guest = fields.Integer('Guest')
    user_price = fields.Float('Grand Total', compute='onchange_calc_sub')
    rodex_profit = fields.Float('Profit', compute='onchange_calc_profit')
    vendor_payment = fields.Float('Total', compute='onchange_calc_sub')

    ##### Cache Odoo12 START #####
    def render_cache_dest_for_gw(self, country_name=[], city_name='', providers=[], limit=99999):
        domain = [('active','=',True)]
        city_cache = []
        if providers:
            provider_destination_ids = []
            for provider in providers:
                if not provider:
                    continue
                # provider = provider.split('_')[0]
                provider_obj = self.env['tt.provider'].search(['|', ('alias', '=', provider), ('code', '=', provider)], limit=1)
                provider_id = provider_obj.id
                provider_destination_ids += [rec.res_id for rec in self.env['tt.provider.code'].sudo().search([('res_model', '=', 'tt.hotel.destination'), ('provider_id', '=', provider_id)]) if rec.res_id]
            domain.append(('id', 'in', provider_destination_ids))
        if country_name:
            country_ids = []
            for rec in country_name:
                country_ids += self.env['res.country'].sudo().search([('name', '=ilike', rec)]).ids
            domain.append(('country_id', 'in', country_ids))

        if city_name:
            domain.append(('name', '=ilike', city_name))

        f2 = open('/var/log/tour_travel/cache_hotel/catalog.txt', 'r')
        f2 = f2.read()
        catalog = json.loads(f2)
        catalog.sort(key=lambda k: k['index'])

        destination_ids = self.env['tt.hotel.destination'].sudo().search(domain, limit=limit).ids
        return destination_ids

    def render_cache_city_for_gw(self, country_name=[], city_name='', providers=[], limit=99999):
        city_ids = []
        city_cache = []
        if providers:
            for provider in providers:
                if not provider:
                    continue
                # provider = provider.split('_')[0]
                provider_obj = self.env['tt.provider'].search(['|', ('alias', '=', provider), ('code', '=', provider)], limit=1)
                provider_id = provider_obj.id
                city_ids += [rec.res_id for rec in self.env['tt.provider.code'].sudo().search([('res_model', '=', 'res.city'), ('provider_id', '=', provider_id)]) if rec.res_id and rec.res_id not in city_ids]

        f2 = open('/var/log/tour_travel/cache_hotel/catalog.txt', 'r')
        f2 = f2.read()
        catalog = json.loads(f2)
        catalog.sort(key=lambda k: k['index'])

        destination_ids = self.render_cache_dest_for_gw(country_name, city_name, providers, limit)
        for city in catalog:
            if city['destination_id'] in destination_ids or city['city_id'] in city_ids:
                city_cache.append(city)
        return city_cache

    def create_cache_city(self):
        json_city = self.render_cache_city()
        filename = "/var/log/tour_travel/cache_city/cache_city.json"
        file = open(filename, 'w')
        file.write(json_city)
        file.close()
        return True

    def update_cache_city(self):
        json_city = self.render_cache_city()
        temp_filename = "/var/log/tour_travel/autocomplete_hotel/autocomplete_cache.json"
        with open(temp_filename, 'r') as f2:
            record = f2.read()
            record = json.loads(record)
            record['city_ids'] = json_city

        file = open(temp_filename, 'w')
        file.write(json.dumps(record))
        file.close()
        return True
    ##### Cache Odoo12 END   #####

    def prepare_facilities(self, view_obj):
        return [{'facility_id': facility.id, 'facility_name': facility.name, 'description': facility.description} for facility in view_obj.facility_ids]

    def prepare_images(self, obj):
        return [{'name': image.name, 'url': image.image_url_complete} for image in obj.images]

    def prepare_images_sql(self, ids):
        a = {}
        if len(ids) == 1:
            self.env.cr.execute("""SELECT pi.hotel_id, pi.name, pi.image_url_complete url FROM product_image pi WHERE pi.hotel_id = """ + str(ids[0]))
        else:
            self.env.cr.execute("""SELECT pi.hotel_id, pi.name, pi.image_url_complete url FROM product_image pi WHERE pi.hotel_id in """ + str(ids))
        for rec in self.env.cr.dictfetchall():
            if not a.get(rec['hotel_id']):
                a[rec['hotel_id']] = []
            a[rec.pop('hotel_id', None)].append(rec)
        return a

    def prepare_provider_codes(self, provider_codes):
        # codes = []
        codes = {}
        for code in provider_codes:
            # codes.append({'provider': code.provider_id.name, 'name': code.name, 'external_id': code.code})
            codes[code.provider_id.code] = code.code
        return codes

    def prepare_landmark_distance(self, landmarks):
        return [{'id': landmark.landmark_id.id, 'name': landmark.landmark_id.name, 'type': landmark.landmark_id.type_id.name,
                 'images': [{'name': rec.name, 'description': rec.description, 'url': rec.image_url_complete} for rec in
                            landmark.landmark_id.image_ids[:3]],
                 'distance': str(landmark.distance) + ' ' + landmark.uom_id, 'url': '#'} for landmark in landmarks]

    def prepare_landmark(self, landmarks):
        # images = [{'name': rec.name, 'description': rec.description, 'url': rec.image_url_complete} for rec in
        #            landmark.image_ids],
        return [{
            'id': landmark.id, 'name': landmark.name, 'type': landmark.type_id.name,
            'images': len(landmark.image_ids) > 1 and landmark.image_ids[0].image_url_complete or '',
            'city': landmark.city_id.name, 'near_by_hotel': len(landmark.hotel_ids)
        } for landmark in landmarks]

    def prepare_countries(self, countries):
        return [{'id': country.id, 'name': country.name} for country in countries]

    def prepare_current_room(self, room_ids):
        a = {'rooms':[], 'price_total':0, 'meal_type': 'No Breakfast',}
        for rec in room_ids:
            a['rooms'].append({
              'description': rec.room_name,
              'qty': 1,
              'pax': {
                  'adult': rec.reservation_id.guest_count,
                  'child': rec.reservation_id.child,
              },
              'extrabed': 0,
              'price_total': rec.sale_price,
            })
            a['price_total'] += rec.sale_price
        return a

    def prepare_pnrs(self, room_ids):
        return [{'issued_code': rec.issued_name, 'status':'issued'} for rec in room_ids]

    # TODO Lepas masking
    def masking_provider(self, provider):
        if provider in ['webbeds', 'fitruums']:
            return 'A1'
        elif provider == 'dida':
            return 'A2'
        elif provider == 'knb':
            return 'A3'
        elif provider == 'miki':
            return 'A4'
        elif provider == 'quantum':
            return 'A5'
        elif provider in ['mg', 'mgholiday']:
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
        else:
            return provider

    # TODO Lepas masking
    def unmasking_provider(self, provider):
        x = self.env['tt.provider'].search([('alias','=',provider)], limit=1)
        if x:
            return x.code
        else:
            return provider

    def get_summary_booking(self, order_number, context):
        res = self.env['tt.reservation.hotel'].sudo().search([('name', '=', order_number)])

        values = {
            'booking_values': {'passengers': res.passenger_ids.read()},
            'checkin': res.checkin_date,
            'checkout': res.checkout_date,
            'duration': res.nights,
            'hotel': res.hotel_id and res.hotel_id.read()[0] or {'name': res.hotel_name,
                                                                 'location': {
                                                                     'address': res.hotel_address,
                                                                     'city': res.hotel_city,
                                                                     'phone': res.hotel_phone,
                                                                 }},
            'current_room': self.prepare_current_room(res.room_detail_ids),
            'search_value': 5,
            'policy': [res.cancellation_policy_str, ],
            'pnrs': self.prepare_pnrs(res.room_detail_ids),
            'name': res.name
        }
        return values

    # Search Data Provider Hotel
    def get_provider_hotel_detail(self, hotel_ids, provider_id):
        list_hotel = []
        try:
            sql_images = self.prepare_images_sql(tuple(hotel_ids))
            for hotel_id in hotel_ids:
                hotel_obj = self.env['tt.hotel'].sudo().browse(hotel_id)
                vals = {
                    'id': str(hotel_obj.id),
                    'name': hotel_obj.name,
                    'rating': hotel_obj.rating,
                    'images': sql_images.get(hotel_obj.id) or [],
                    # 'images': self.prepare_images(hotel_obj),
                    # 'images': [],
                    'prices': [],
                    'description': hotel_obj.description,
                    'location': {
                        'city_id': hotel_obj.hotel_partner_city_id.id,
                        'address': hotel_obj.address,
                        'city': hotel_obj.hotel_partner_city_id.name,
                        'state': hotel_obj.state_id.name,
                        'district': hotel_obj.district_id.name,
                        'kelurahan': hotel_obj.kelurahan,
                        'zipcode': hotel_obj.zip
                    },
                    # 'hotel_id_provider': self.get_provider_code(hotel_obj.provider_hotel_ids),
                    'telephone': hotel_obj.phone,
                    'fax': hotel_obj.fax,
                    'ribbon': hotel_obj.ribbon,
                    'facilities': self.prepare_facilities(hotel_obj),
                    'lat': hotel_obj.lat,
                    'long': hotel_obj.long,
                    'state': hotel_obj.state,
                    'external_code': self.prepare_provider_codes(hotel_obj.provider_hotel_ids),
                    'near_by_facility': self.prepare_landmark_distance(hotel_obj.landmark_ids),
                }
                list_hotel.append(vals)
            return list_hotel
        except:
            return list_hotel

    def get_provider_city_detail(self, city_id):
        return {
            'id': city_id.id,
            'name': city_id.name,
            'city_id': city_id.id,
            'country_name': city_id.country_id.name,
            'image': city_id.image_url,
            'banner_urls': [{'url': rec.image_url, 'desc': ''} for rec in city_id.banner_ids],
            'hotel_qty': len(city_id.hotel_ids.ids),
        }

    # Search Hotel Availability by ID
    def get_hotel_detail(self, hotel_ids, start_date, end_date, user_qty, room_qty, child_ages=[]):
        list_hotel = []
        from_dt = fields.Datetime.from_string(start_date)
        to_dt = fields.Datetime.from_string(end_date)
        time_delta = to_dt - from_dt - timedelta(days=1)
        for hotel_id in hotel_ids:
            hotel_obj = self.env['tt.hotel'].sudo().browse(hotel_id)
            hotel_valid = True
            room_info_ids = []
            all_room_ava = 0
            all_room_user = 0
            room_this_day = []
            if hotel_obj.provider == 'cms':
                for room_id in hotel_obj.room_info_ids:
                    a = {
                        'room_id': room_id.id,
                        'room_code': str(room_id.id),
                        'room_name': room_id.name,
                        'room_rates': [],
                        'total_rate': 0,
                        'meal_type': room_id.meal_type,
                        'max_guest': room_id.max_guest,
                        'cancellation_policy_id': room_id.cancellation_policy.id,
                        'message': room_id.message,
                        'availability': room_id.today_availability_count,
                        'room_images': self.prepare_images(room_id),
                    }
                    min_room_ava = 0
                    min_room_user = 0
                    room_valid = True
                    for i in range(time_delta.days + 1):
                        now_date = from_dt + timedelta(days=i)
                        room_ava, room_user = room_id.get_room_available(now_date, child_ages)
                        # room_ava, room_user = room_id.get_room_available(now_date)
                        if room_ava > 0:
                            today_rate = room_id.get_price_by_date(1, now_date)
                            if today_rate[0]['room_rate']:
                                a['room_rates'].append(today_rate)
                                a['availability'] = a['availability'] > room_ava and room_ava or a['availability']
                                a['total_rate'] += today_rate[0]['room_rate']
                            else:
                                room_valid = False
                        else:
                            room_valid = False
                            break
                        min_room_ava = min_room_ava < room_ava and min_room_ava or room_ava
                        min_room_user = min_room_user < room_user and min_room_user or room_user
                    if room_valid:
                        room_this_day.append(a)
                        all_room_ava += min_room_ava
                        all_room_user += min_room_user
                if all_room_ava >= room_qty and all_room_user >= user_qty + len(child_ages):
                    room_info_ids += room_this_day
                else:
                    hotel_valid = False

            if hotel_valid:
                vals = {
                    'hotel_id': str(hotel_obj.id),
                    'hotel_code': hotel_obj.provider == 'cms' and 'cms,' + str(hotel_obj.id) + ',' + start_date + ',' + end_date or '',
                    'hotel_name': hotel_obj.name,
                    'location': {
                        'city_id': hotel_obj.hotel_partner_city_id.id,
                        'address': hotel_obj.address,
                        'city': hotel_obj.hotel_partner_city_id.name,
                        'state': hotel_obj.state_id.name,
                        'district': hotel_obj.district_id.name,
                        'kelurahan': hotel_obj.kelurahan,
                        'zipcode': hotel_obj.zip
                    },
                    'rating': hotel_obj.rating,
                    'hotel_facilities': self.prepare_facilities(hotel_obj),
                    'telephone': hotel_obj.phone,
                    'facsimile': hotel_obj.fax,
                    'city_id': hotel_obj.hotel_partner_city_id.id,
                    'ribbon': hotel_obj.ribbon,
                    'description': hotel_obj.description,
                    'hotel_rooms': room_info_ids,
                    'currency_id': hotel_obj.room_info_ids and hotel_obj.room_info_ids[0].currency_id.name or False,
                    'hotel_package_rooms': False,
                    'hotel_images': self.prepare_images(hotel_obj),
                    'provider': hotel_obj.provider,
                    'hotel_id_provider': hotel_obj.provider_hotel_ids.filtered(lambda x: x.provider_id.id == 4).code
                }
                # vals['hotel_code'] = 'cms'
                # vals['hotel_code'] += ',' + str(vals['hotel_id'])
                list_hotel.append(vals)
        return list_hotel

    # Search By City ID
    def search_hotel_1_1(self, city_id, start_date, end_date, user_qty, room_qty, child_ages=[]):
        hotel_ids = self.env['res.city'].sudo().browse(city_id).hotel_ids.ids
        return self.get_hotel_detail(hotel_ids, start_date, end_date, user_qty, room_qty, child_ages)

    def search_hotel_1_2(self, start_date, end_date, user_qty, room_qty):
        hotel_objs = self.env['tt.hotel'].search([])
        list_hotel = []
        from_dt = fields.Datetime.from_string(start_date)
        to_dt = fields.Datetime.from_string(end_date)
        time_delta = to_dt - from_dt - timedelta(days=1)
        for hotel_obj in hotel_objs:
            hotel_valid = True
            room_info_ids = []
            all_room_ava = 0
            all_room_user = 0
            room_this_day = []
            for room_id in hotel_obj.room_info_ids:
                a = {
                    'room_id': room_id.id,
                    'room_name': room_id.name,
                    'room_rates': [],
                    'meal_type': room_id.meal_type,
                    'max_guest': room_id.max_guest,
                    'cancelation_policy': room_id.cancellation_policy,
                    'message': room_id.message,
                    'availability': room_id.today_availability_count,
                    'room_images': self.prepare_images(room_id),
                }
                min_room_ava = 0
                min_room_user = 0
                room_valid = True
                for i in range(time_delta.days + 1):
                    now_date = from_dt + timedelta(days=i)
                    room_ava, room_user = room_id.get_room_available(now_date)
                    if room_ava > 0:
                        # a['room_rates'] += room_id.get_price_by_date(1, now_date)
                        a['room_rates'] += room_id.sale_price
                        a['availability'] = a['availability'] < room_ava and room_ava or a['availability']
                    else:
                        room_valid = False
                        break
                    min_room_ava = min_room_ava < room_ava and min_room_ava or room_ava
                    min_room_user = min_room_user < room_user and min_room_user or room_user
                if room_valid:
                    room_this_day.append(a)
                    all_room_ava += min_room_ava
                    all_room_user += min_room_user
            if all_room_ava >= room_qty and all_room_user >= user_qty:
                room_info_ids += room_this_day
            else:
                hotel_valid = False
                break
            if hotel_valid:
                vals = {
                    'hotel_id': hotel_obj.id,
                    'hotel_name': hotel_obj.name,
                    'location': {
                        'city_id': hotel_obj.hotel_partner_city_id.id,
                        'address': hotel_obj.address,
                        'city': hotel_obj.hotel_partner_city_id.name,
                        'state': hotel_obj.state_id.name,
                        'district': hotel_obj.district_id.name,
                        'kelurahan':hotel_obj.kelurahan,
                        'zipcode':hotel_obj.zip
                    },
                    'rating': hotel_obj.rating,
                    'hotel_facilities': self.prepare_facilities(hotel_obj),
                    'telephone': hotel_obj.phone,
                    'facsimile': hotel_obj.fax,
                    'currency_id': hotel_obj.room_info_ids and hotel_obj.room_info_ids[0].currency_id or False,
                    'ribbon': hotel_obj.ribbon,
                    'hotel_rooms': room_info_ids,
                    'hotel_package_rooms': False,
                    'hotel_images': self.prepare_images(hotel_obj)
                }
                list_hotel.append(vals)
        return list_hotel

    @api.multi
    def search_hotel_1(self):
        return self.search_hotel_1_1(self.rate_id.room_info_id.hotel_id.hotel_partner_city_id.id, self.date_start,
                                     self.date_end, self.guest, self.nights)

    def get_backend_object(self, provider_name, hotel_id):
        try:
            if hotel_id:
                provider_id = self.env['tt.provider'].sudo().search([('code', '=', self.unmasking_provider(provider_name))])
                code_ids = self.env['tt.provider.code'].sudo().search([('provider_id', '=', provider_id.id), ('code', 'ilike', hotel_id.split('~')[0])])
                return code_ids and code_ids[0].hotel_id or False
            else:
                return False
        except:
            return False

    # Jenis Type: Hotel, City, Country, State dll
    def create_new_record(self, type, vals):
        create_obj = False
        if type == 'hotel':
            a = self.env['tt.provider.code'].sudo().search([('code', '=', vals['id']), ('hotel_id', '!=', False)], limit=1)
            if a:
                return a[0].hotel_id.id
            provider = vals['provider']
            vals.update({
                'state': 'draft',
                'provider': False,
                'name': vals['name'],
                'hotel_partner_id': self.env.ref('tt_hotel.hotel_management_admin').id,
                'hotel_partner_city_id': vals['location']['city_id'],
                'lat': vals['lat'],
                'long': vals['long'],
            })
            try:
                vals_images = vals.pop('images')
                create_obj = self.env['tt.hotel'].sudo().create(vals)
                self.env['tt.provider.code'].sudo().create({
                    'hotel_id': create_obj.id,
                    'name': vals['name'],
                    'code': vals['id'],
                    'provider_id': self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1).id,
                })
                for rec in vals_images:
                    self.env['product.image'].create({
                        'hotel_id': create_obj.id,
                        'name': rec['name'],
                        'image_url_complete': rec['url'],
                    })
                return create_obj.id
            except:
                return False

    def _create_contact(self, vals, context):
        if vals.get('contact_id'):
            cust_partner_obj = self.env['tt.customer'].sudo().browse(int(vals['contact_id']))
            return cust_partner_obj
        else:
            country_nationality = self.env['res.country'].search([('code', '=', vals.pop('nationality_code'))])
            country_country = self.env['res.country'].search([('code', '=', vals.pop('country_code'))])
            vals.update({
                'nationality_id': country_nationality and country_nationality[0].id or False,
                # 'country_id': country_country and country_country[0].id or False,
                'agent_id': context['agent_id'],
                'gender': vals['title'] and 'male' if vals['title'].lower() in ('mr', 'mstr') else 'female' or False,
            })
            vals.pop('title')
            return self.env['tt.customer'].sudo().create(vals)

    def _create_guests(self, passenger_ids, booker_id):
        ids = []
        for guest in passenger_ids:
            if guest.get('passenger_id'):
                ids.append(int(guest['passenger_id']))
            else:
                new_guest = self.env['tt.customer'].sudo().search([
                    ('first_name', '=', guest['first_name']),
                    ('last_name', '=', guest['last_name'])
                ], limit=1)
                if not new_guest:
                    new_guest = self.env['tt.customer'].sudo().create({
                        # 'title': guest['title'],
                        'first_name': guest['first_name'],
                        'last_name': guest['last_name'],
                        # 'date': guest['birth_date'],
                        'birth_date': guest['birth_date'],
                        # 'pax_type': guest['pax_type'],
                        # 'country_of_issued_code': guest['country_of_issued_code'],
                        'passport_expdate': guest.get('passport_expdate') and guest['passport_expdate'] or '0001-01-01',
                        'passport_number': guest.get('passport_number'),
                        'agent_id': booker_id.agent_id.id,
                        # 'contact_id': booker_id.id,
                        'gender': guest['title'] and 'male' if guest['title'].lower() in ('mr', 'mstr') else 'female' or False,
                    })
                ids.append(new_guest.id)
        return ids

    def prepare_resv_value(self, backend_hotel_obj, hotel_obj, check_in, check_out, room_rates,
                           booker_obj, contact_obj, provider_data, special_req, guest_list,
                           ho_id, agent_id, cancellation_policy, hold_date):
        room_count = 0
        for rec in room_rates:
            room_count += sum(int(a['qty']) or 1 for a in rec['rooms'])
        vals = {
            'name': 'New',
            # 'name': backend_hotel_obj and backend_hotel_obj.sudo().name + check_in + check_out or hotel_id + check_in + check_out,
            'state': 'draft',
            # 'number': os_res_no,
            # 'provider_id': provider_id,
            'hotel_id': backend_hotel_obj and backend_hotel_obj.id or False,
            'hotel_name': backend_hotel_obj and backend_hotel_obj.sudo().name or hotel_obj['name'],
            'hotel_address': backend_hotel_obj and backend_hotel_obj.sudo().address or hotel_obj['address'],
            'hotel_rating': backend_hotel_obj and backend_hotel_obj.sudo().rating or hotel_obj.get('rating'),
            'hotel_city': backend_hotel_obj and backend_hotel_obj.sudo().city_id.name or hotel_obj['city'],
            'hotel_phone': backend_hotel_obj and backend_hotel_obj.sudo().phone or hotel_obj['phone'],
            'checkin_date': check_in,
            'checkout_date': check_out,
            'room_count': room_count,
            'nights': relativedelta(dt.strptime(check_out, "%Y-%m-%d"), dt.strptime(check_in, "%Y-%m-%d")).days,
            'booker_id': booker_obj.id, #
            'contact_id': contact_obj.id, #
            'contact_name': contact_obj.name, #
            'contact_email': contact_obj.email, #
            'contact_phone': "%s - %s" % (contact_obj.phone_ids[0].calling_code,contact_obj.phone_ids[0].calling_number),
            'display_mobile': False, #
            'adult': len(list(filter(lambda i: i['pax_type'] == 'ADT', guest_list))),
            'provider_data': provider_data,
            'ho_id': ho_id,
            'agent_id': agent_id,
            'special_req': special_req,
            # 'sub_agent_id': cust_partner_obj.agent_id.id,
            'child': len(list(filter(lambda i: i['pax_type'] == 'CHD', guest_list))),
            'infant': len(list(filter(lambda i: i['pax_type'] == 'INF', guest_list))),
            'cancellation_policy_str': ';; '.join([x['cancellation_string'] for x in cancellation_policy]) if isinstance(cancellation_policy, list) else cancellation_policy,
            # 'norm_str': ';; '.join(norm_str) if isinstance(norm_str, list) else norm_str,
            'hold_date': hold_date,
        }
        return vals

    def _get_exists_passenger(self, passengers):
        res = []
        for rec in passengers:
            if rec['passenger_id']:
                psg_obj = self.env['tt.customer'].browse(int(rec['passenger_id']))
                if psg_obj:
                    res.append(psg_obj.id)
                else:
                    rec['passenger_id'] = False  # wemust flag False for create new passenger
        return res

    def get_exist_sale_charge(self, charge_code, foreign_amount, vendor_currency_id, amount, sale_price_ids):
        exist = False
        for price_id in sale_price_ids:
            if price_id['charge_code'] == charge_code and price_id['amount'] == amount:
                exist = True
                price_id['pax_count'] += 1
                break
        if not exist:
            sale_price_ids.append({'charge_code': charge_code, 'foreign_amount': foreign_amount, 'foreign_currency_id': vendor_currency_id, 'amount': amount, 'pax_count': 1})

    # Todo Set Agent ID copy dari line 702 transport_booking Cek Klo Cor/Por
    # Todo Create Contact fungsi sendiri
    # Todo cek apakah detail guest sdah ada kumpul kan

    # def create_reservation(self, hotel_obj, provider_name, cust_names, check_in, check_out, room_rates,
    #                        booker_detail, acquirer_id, provider_data='', special_req='', cancellation_policy='', context={}):
    def create_reservation(self, req, context={}):
        provider_data = req.get('provider_data', '')
        special_req = req.get('special_request', 'No Special Request')
        cancellation_policy = req.get('cancellation_policy', '')
        norm_str = req.get('norm_str', '')

        context['agent_id'] = self.sudo().env['res.users'].browse(context['co_uid']).agent_id.id
        context['ho_id'] = context.get('co_ho_id') and context['co_ho_id'] or self.sudo().env['res.users'].browse(context['co_uid']).ho_id.id

        for idx,pax in enumerate(req['passengers']):
            pax.update({
                'sequence': idx,
                'gender': 'male' if pax['title'] in ['MR', 'MSTR'] else 'female'
            })

        booker_obj = self.env['tt.reservation.hotel'].create_booker_api(req['booker'], context)
        contact_obj = self.env['tt.reservation.hotel'].create_contact_api(req['contact'][0],booker_obj,context)
        list_passenger_value = self.env['tt.reservation.hotel'].create_passenger_value_api(req['passengers'])
        list_customer_id = self.env['tt.reservation.hotel'].create_customer_api(req['passengers'], context, booker_obj.seq_id, contact_obj.seq_id)

        # fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
        for idx, rec in enumerate(list_passenger_value):
            rec[2].update({
                'customer_id': list_customer_id[idx].id
            })

        for psg in list_passenger_value:
            util.pop_empty_key(psg[2])

        backend_hotel_obj = self.get_backend_object(req['price_codes'][0]['provider'], req['hotel_obj']['id'])
        vals = self.prepare_resv_value(backend_hotel_obj, req['hotel_obj'], req['checkin_date'], req['checkout_date'], req['price_codes'],
                                       booker_obj, contact_obj, provider_data, special_req, req['passengers'],
                                       context['ho_id'], context['agent_id'], cancellation_policy, context.get('hold_date', False))

        if req.get('member'):
            customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', req['acquirer_seq_id'])], limit=1)[0]
        else:
            customer_parent_id = booker_obj.customer_parent_ids[0]

        customer_parent_type_id = customer_parent_id.customer_parent_type_id.id
        customer_parent_id = customer_parent_id.id

        vals.update({
            'user_id': context['co_uid'],
            'sid_booked': context['signature'],
            'booker_id': booker_obj.id,
            'contact_title': req['contact'][0]['title'],
            'contact_id': contact_obj.id,
            'contact_name': contact_obj.name,
            'contact_email': contact_obj.email,
            'contact_phone': contact_obj.phone_ids and "%s - %s" % (contact_obj.phone_ids[0].calling_code, contact_obj.phone_ids[0].calling_number) or '-',
            'passenger_ids': list_passenger_value,
            'customer_parent_id': context.get('co_customer_parent_id',False) or customer_parent_id,
            'customer_parent_type_id': context.get('co_customer_parent_type_id',False) or customer_parent_type_id,
        })

        resv_id = self.env['tt.reservation.hotel'].create(vals)
        resv_id.hold_date = context.get('hold_date', False)
        # resv_id.write({'passenger_ids': [(6, 0, [rec[0].id for rec in passenger_objs])]})

        ## CURRENCY 22 JUN - IVAN
        currency = ''
        for price_code in req['price_codes']:
            currency = price_code['currency']
        if currency:
            currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
            if currency_obj:
                resv_id.currency_id = currency_obj.id

        for price_obj in req['price_codes']:
            for room_rate in price_obj['rooms']:
                vendor_currency_id = self.env['res.currency'].sudo().search([('name', '=', room_rate['currency'])], limit=1).id
                provider_id = self.env['tt.provider'].search([('code','=', self.unmasking_provider(price_obj['provider']))], limit=1).id
                detail = self.env['tt.hotel.reservation.details'].sudo().create({
                    'provider_id': provider_id,
                    'reservation_id': resv_id.id,
                    'date': fields.Datetime.from_string(req['checkin_date']),
                    'date_end': fields.Datetime.from_string(req['checkout_date']),
                    'sale_price': float(room_rate['price_total']),
                    'prov_sale_price': float(room_rate['price_total_currency']),
                    'prov_currency_id': vendor_currency_id,
                    'room_name': room_rate['description'],
                    'room_vendor_code': price_obj['price_code'],
                    'room_type': room_rate['type'],
                    'meal_type': price_obj['meal_type'],
                    'commission_amount': float(room_rate.get('commission', 0)),
                    # 'supplements': ';; '.join([json.dumps(x) for x in room_rate['supplements']]),
                    'supplements': ';; '.join([x['name'] for x in room_rate['supplements']]),
                })
                self.env.cr.commit()
                total_price = 0
                for charge_id in room_rate['nightly_prices']:
                    charge_id_price = 0
                    for sc_per_night in charge_id['service_charges']:
                        charge_id_price += sc_per_night['total'] if sc_per_night['charge_type'] in ['FARE', 'TAX', 'ROC'] else 0
                    total_price += charge_id_price
                    self.env['tt.room.date'].sudo().create({
                        'detail_id': detail.id,
                        'date': charge_id['date'],
                        'sale_price': charge_id_price, #charge_id['price_currency'],
                        'commission_amount': charge_id['commission'],
                        'meal_type': '',
                    })
                    # Merge Jika Room type yg sama 2
                    for scs in charge_id['service_charges']:
                        scs.update({
                            'resv_hotel_id': resv_id.id,
                            'total': scs['amount'] * scs['pax_count'],
                            'currency_id': self.env['res.currency'].get_id(scs.get('currency'), default_param_idr=True),
                            'foreign_currency_id': self.env['res.currency'].get_id(scs.get('foreign_currency'), default_param_idr=True),
                            'description': '',
                            'ho_id': context.get('co_ho_id') and context['co_ho_id'] or (resv_id.ho_id.id if resv_id.ho_id else '')
                        })
                        self.env['tt.service.charge'].create(scs)

                detail.sale_price = total_price
        # resv_id.total = total_rate

        # Create provider_booking_ids
        vend_hotel = self.env['tt.provider.hotel'].create({
            'provider_id': provider_id or '',
            'booking_id': resv_id.id,
            'pnr': '0',
            'pnr2': '',
            'balance_due': resv_id.total_nta,
            'total_price': resv_id.total_nta,
            'checkin_date': req['checkin_date'],
            'checkout_date': req['checkout_date'],
            'hotel_id': resv_id.hotel_id.id,
            'hotel_name': resv_id.hotel_name,
            'hotel_address': resv_id.hotel_address,
            'hotel_city': resv_id.hotel_city,
            'hotel_phone': resv_id.hotel_phone,
            'sid': context['sid'],
        })

        vend_hotel.create_service_charge(resv_id.sale_service_charge_ids)

        resv_id.action_booked(context)

        ## PAKAI VOUCHER
        if req.get('voucher'):
            resv_id.voucher_code = req['voucher']['voucher_reference']

        return self.get_booking_result(resv_id.id, context)

    def create_reservation_old(self, provider_name, hotel_id, cust_names, check_in, check_out, room_rates, cancellation_str, booker_detail, guest_count=0, os_res_no='', provider_data='', email='', mobile='', special_req=''):
    # def create_reservation(self, provider_name, hotel_id, hotel_name, hotel_city_id, room_count, cust_name, check_in, check_out, room_rates, guest_count=0, os_res_no='', provider_data='', email='', mobile='', special_req=''):
        cust_name = cust_names[0]
        total_rate = 0
        total_commision = 0
        customer_name = booker_detail['prefix'].upper() + '. ' + booker_detail['first_name'] + ' ' + booker_detail['last_name']
        cust_partner_obj = self.env['tt.customer.contact'].sudo().browse(int(booker_detail['id']))
        if not cust_partner_obj:
            cust_partner_obj = self.env['tt.customer.contact'].sudo().search([('name', '=', customer_name)], limit=1)
        provider_name_1 = provider_name[:3] == 'cms' and 'cms' or provider_name
        # provider_id = self.env['tt.api.connector'].sudo().search([('name', '=', provider_name_1.upper())]).id
        provider_id = provider_name == 'cms' and 1 or 2
        backend_hotel_obj = self.get_backend_object(provider_name, hotel_id)
        vals = self.prepare_resv_value(backend_hotel_obj, hotel_id, os_res_no, provider_id, check_in, check_out, room_rates, cust_partner_obj, customer_name, email, mobile, guest_count, provider_data, special_req, cancellation_str, cust_names)

        resv_id = self.env['tt.reservation.hotel'].sudo().create(vals)
        # Klo dia CMS dicari juga room rate nya
        if provider_name == 'cms':
            date = fields.Datetime.from_string(check_in)
            to_dt = fields.Datetime.from_string(check_out)
            time_delta = to_dt - date - timedelta(days=1)
            for room_rate in room_rates:
                for i in range(time_delta.days + 1):
                    now_date = date + timedelta(days=i)
                    room_code = room_rate['room_id'].split(",",1)
                    room_id = int(room_code[0])
                    room_price = len(room_code) > 2 and int(room_code[1]) or 0
                    room_info_obj = self.env['tt.room.info'].browse(room_id)
                    thisday_rate = room_info_obj.sudo().get_price_by_date(1, now_date)[0]
                    today_room_rate = room_info_obj.spc_room_rate_ids.filtered(lambda line: line.start_date <= str(now_date) and line.end_date > str(now_date)
                                                                     and getattr(line, 'apply_on_%s' % now_date.strftime("%A").lower()))
                    commission = thisday_rate['commision']

                    self.env['tt.hotel.reservation.details'].sudo().create({
                        'reservation_id': resv_id.id,
                        'date': fields.Date.to_string(now_date),
                        'room_rate_id': today_room_rate and today_room_rate[0].id or 0,
                        'sale_price': thisday_rate and thisday_rate['room_rate'] or room_price,
                        'room_name': room_info_obj.name,
                        'room_type': room_info_obj.room_type_id.name,
                        'commission_amount': commission,
                    })
                    total_rate += thisday_rate and int(thisday_rate['room_rate']) or room_price
                    total_commision += thisday_rate and commission or 0
        else:
            for room_rate in room_rates:
                self.env['tt.hotel.reservation.details'].create({
                    'reservation_id': resv_id.id,
                    'sale_price': float(room_rate['price']),
                    'room_name': room_rate['room_name'],
                    'room_type': room_rate['room_type'],
                    'commision_amount': int(room_rate['commission']),
                })
                total_rate += float(room_rate['price'])
                total_commision += int(room_rate['commission'])

        resv_id.total_sale_price = total_rate
        resv_id.total_commission_amount = total_commision

        return (str(resv_id.id), resv_id.name)

    def payment_hotel(self, req, context):
        return self.env['tt.reservation'].payment_reservation_api('hotel', req, context)

    # Update Reservation
    def update_from_provider(self, resv_id, prov_code, state='request'):
        resv_obj = self.browse(resv_id)
        resv_obj.write({
            'state': state,
            'provider_data': prov_code,
        })
        return True

    @api.multi
    def create_reservation_dummy(self):
        return self.create_reservation('cms', 'test01', 'Hotel MA3', 'Budy Budiarto', '2017-08-29', '2017-08-31', 2, [{'room_id': 1, 'room_name': 'Double Deluxe', 'room_type': 'Deluxe', 'price': 150000, 'commission': 30000},{'room_id': 1, 'room_name': 'Double Deluxe', 'room_type': 'Deluxe', 'price': 150000, 'commission': 30000}], 'tingkiwingky')
        # return self.create_reservation('cms', 'test01', 'Hotel MA3', 269, 1, 'Budy Budiarto', '2017-08-29', '2017-08-31', 2, [{'price': 150000, 'commission': 30000},{'price': 150000, 'commission': 30000},{'price': 150000, 'commission': 30000}], '{"nama": "tingkiwingky", "nama2": "dipsy"}')

    def validation_booking(self, resv_id):
        resv_obj = self.env['tt.reservation.hotel'].browse(resv_id)
        for room_id in resv_obj.room_detail_ids:
            if room_id.room_info_id:
                self.env['tt.room.info.booking'].create({
                    'date': room_id.date,
                    'room_info_id': room_id.room_info_id.id,
                    'qty': 1,
                    'reservation_id': resv_id,
                })

    def reservation_success(self, resv_name, user_id):
        self.env['tt.reservation.hotel'].sudo().search([('name', 'ilike', resv_name)], limit=1).action_confirm({'user_id':user_id})

    def reservation_issued(self, resv_name, user_id):
        return self.env['tt.reservation.hotel'].sudo().search([('name', 'ilike', resv_name)], limit=1).action_issued({'user_id':user_id})

    @api.multi
    def reservation_success_dummy(self):
        last = self.env['tt.reservation.hotel'].search([('state', '=', 'confirm')], limit=1)
        self.reservation_success(last.id)

    # Todo: masukan tipe validasi kamar dan perhitungan jumlah tiket
    def check_validation(self, room_id):
        # Fungsi digunakan untuk menentukan apakah ruangan akan langsung tervalidasi apakah dia bakal langsung kurangi
        # aviabilty atau kurangi stok tiket
        room = self.env['tt.room.info'].sudo().browse(room_id)

        return True

    def prepare_nightly_price(self, nightly, meal_type='Room Only'):
        return [{
            'date': str(night.date),
            'currency': night.currency_id.name,
            'sale_price': night.sale_price,
            'meal_type': night.meal_type or meal_type,
        } for night in nightly]


    def prepare_booking_room(self, lines, customers):
        vals = []
        for room in lines:
            data = {
                # 'id': room.id,
                'prov_issued_code': room.issued_name,
                'prov_booking_code': room.name,
                'provider': room.provider_id.code,
                'dates': self.prepare_nightly_price(room.room_date_ids, room.room_info_id and room.room_info_id.meal_type or room.meal_type),
                'room_name': room.room_info_id and room.room_info_id.name or room.room_name,
                'room_vendor_code': room.room_vendor_code,
                'room_type': room.room_type,
                'room_rate': room.sale_price,
                'person': room.room_info_id and room.room_info_id.max_guest or 2,
                'currency': room.currency_id and room.currency_id.name,
                'meal_type': room.room_info_id and room.room_info_id.meal_type or room.meal_type,
            }
            vals.append(data)
        return vals

    def prepare_passengers(self, customers):
        return [cust.to_dict() for cust in customers]

    def prepare_bookers(self, bookers):
        return {
            'booker_seq_id': bookers['id'],
            'calling_code': bookers['nationality_id']['phone_code'],
            'country_code': bookers['nationality_id']['code'],
            'email': bookers['email'],
            'first_name': bookers['first_name'],
            'last_name': bookers['last_name'] or '',
            'mobile': bookers['phone_ids'] and bookers['phone_ids'][0]['calling_number'] or '',
            'nationality_code': bookers['nationality_id']['code'],
            'nationality_name': bookers['nationality_id']['name'],
            'title': bookers['gender'] == 'male' and 'MR' or bookers['marital_status'] in ['married','widowed'] and 'MRS' or 'MS',
            'work_phone': bookers['phone_ids'] and bookers['phone_ids'][0]['calling_number'] or '',
        }

    def prepare_service_charge(self, cost_sc, obj_pnr):
        sc_value = {}
        for p_sc in cost_sc:
            p_charge_type = p_sc.charge_type
            pnr = p_sc.description or obj_pnr
            if not sc_value.get(pnr):
                sc_value[pnr] = {}
            if not sc_value[pnr].get(p_charge_type):
                sc_value[pnr][p_charge_type] = {}
                sc_value[pnr][p_charge_type].update({
                    'amount': 0,
                    'foreign_amount': 0,
                })

            if p_charge_type == 'RAC' and p_sc.charge_code != 'rac':
                if p_charge_type == 'RAC' and 'csc' not in p_sc.charge_code:
                    continue

            sc_value[pnr][p_charge_type].update({
                'charge_code': p_sc.charge_code,
                'currency': p_sc.currency_id.name,
                'foreign_currency': p_sc.foreign_currency_id.name,
                'amount': sc_value[pnr][p_charge_type]['amount'] + (p_sc.amount * p_sc.pax_count),
                # 'amount': p_sc.amount,
                'foreign_amount': sc_value[pnr][p_charge_type]['foreign_amount'] + (p_sc.foreign_amount * p_sc.pax_count),
                # 'foreign_amount': p_sc.foreign_amount,
            })

        return sc_value

    # def get_service_charge_details(self): COPY dri
    def prepare_service_charge_detils(self, cost_sc, obj_pnr):
        sc_value = {}
        for p_sc in cost_sc:
            p_charge_type = p_sc.charge_type
            pnr = obj_pnr if not p_sc.description or p_sc.description == '0' else p_sc.description
            commission_agent_id = p_sc.commission_agent_id

            # if p_charge_type == 'RAC' and p_sc.charge_code != 'rac':
            #     if p_charge_type == 'RAC' and 'csc' not in p_sc.charge_code:
            #         continue

            if p_charge_type == 'RAC' and commission_agent_id:
                continue

            if not sc_value.get(pnr):
                sc_value[pnr] = {}
            if not sc_value[pnr].get(p_charge_type):
                sc_value[pnr][p_charge_type] = []

            sc_value[pnr][p_charge_type].append({
                'charge_code': p_sc.charge_code,
                'currency': p_sc.currency_id.name,
                'foreign_currency': p_sc.foreign_currency_id.name,
                'amount': p_sc.amount,
                'pax_type': p_sc.pax_type,
                'foreign_amount': p_sc.foreign_amount,
            })

        result = []
        for pnr, pnr_data in sc_value.items():
            base_fare_ori = Decimal("0.0")
            base_tax_ori = Decimal("0.0")
            base_upsell_ori = Decimal("0.0")
            base_upsell_adj = Decimal("0.0")
            base_discount_ori = Decimal("0.0")
            base_agent_commission = Decimal("0.0")
            base_agent_commission_ori = Decimal("0.0")
            base_agent_commission_charge = Decimal("0.0")
            base_commission_vendor = Decimal("0.0")
            base_hidden_commission_ho = Decimal("0.0")
            base_hidden_fee_ho = Decimal("0.0")
            base_hidden_vat_ho = Decimal("0.0")
            base_vendor_vat = Decimal("0.0")
            base_fee_ho = Decimal("0.0")
            base_vat_ho = Decimal("0.0")
            base_commission_ho = Decimal("0.0")

            pax_type = ''

            for charge_type, service_charges in pnr_data.items():
                for sc in service_charges:
                    sc_amount = Decimal(str(sc['amount']))
                    '''
                        GENERAL     |   PROVIDER    |   AGENT   |   CUSTOMER    |   Pricing notes
                        FARE        |   ROC         |   ROC     |   ROC         |
                        TAX         |   RAC         |   RAC     |   RAC         |
                        ROC         |   RACHSP      |   RACHSA  |   -           |
                        DISC        |   ROCHSP      |   ROCHSA  |   -           |   HO service fee
                        RAC         |   RACHVP      |   RACHVA  |   -           |
                        RACCHG      |   ROCHVP      |   ROCHVA  |   -           |   HO tax of service fee
                        ROCCHG      |   RACAVP      |   RACAVA  |   RACAVC      |
                        RACUA       |   ROCAVP      |   ROCAVA  |   ROCAVC      |   HO tax of commission fee
                        ROCUA       |               |           |   
                    '''
                    charge_code = sc.get('charge_code', '')
                    if charge_type == 'FARE':
                        base_fare_ori += sc_amount
                    elif charge_type == 'TAX':
                        base_tax_ori += sc_amount
                    elif charge_type == 'RAC':
                        base_agent_commission += sc_amount
                        base_commission_vendor += sc_amount
                        base_agent_commission_ori += sc_amount
                    elif charge_type in ['RACUA', 'RACCHG']:
                        base_commission_vendor += sc_amount
                        base_agent_commission_ori += sc_amount
                        base_agent_commission_charge += sc_amount
                    elif charge_type in ['ROCUA', 'ROCCHG']:
                        pass
                    elif charge_type == 'DISC':
                        base_discount_ori += sc_amount
                    elif charge_type in ['RACHSP', 'RACHVP']:
                        base_commission_vendor += sc_amount
                        base_hidden_commission_ho += sc_amount
                    elif charge_type == 'ROCHSP':
                        base_hidden_fee_ho += sc_amount
                    elif charge_type == 'ROCHVP':
                        base_hidden_vat_ho += sc_amount
                    elif charge_type == 'RACAVP':
                        base_commission_vendor += sc_amount
                    elif charge_type == 'ROCAVP':
                        base_vendor_vat += sc_amount
                    elif charge_type in ['RACHSA', 'RACHVA', 'RACAVA']:
                        base_commission_ho += sc_amount
                    elif charge_type in ['ROCHVA', 'ROCAVA']:
                        base_vat_ho += sc_amount
                    elif charge_type == 'ROCHSA':
                        base_fee_ho += sc_amount
                    elif charge_type == 'RACAVC':
                        base_commission_ho += sc_amount
                    elif charge_type == 'ROCAVC':
                        base_vat_ho += sc_amount
                    elif charge_type == 'ROC' and charge_code[-3:] == 'adj':
                        base_upsell_adj += sc_amount
                    else:
                        base_upsell_ori += sc_amount

                    if not pax_type:
                        pax_type = sc['pax_type']

            base_price_ori = base_fare_ori + base_tax_ori
            base_price = base_price_ori + base_upsell_ori + base_discount_ori + base_upsell_adj
            base_nta_vendor = base_price + base_commission_vendor + base_vendor_vat - base_upsell_adj

            base_fare = base_fare_ori
            base_tax = base_tax_ori
            base_upsell = base_upsell_ori + base_upsell_adj
            base_discount = base_discount_ori
            if base_hidden_commission_ho != 0:
                base_upsell -= abs(base_hidden_commission_ho)
                if base_tax != 0:
                    base_tax += abs(base_hidden_commission_ho)
                else:
                    base_fare += abs(base_hidden_commission_ho)
            if base_commission_ho != 0:
                base_upsell -= abs(base_commission_ho)

            base_nta = base_price - abs(base_agent_commission)
            base_commission_ho_ori = base_commission_ho + base_hidden_commission_ho

            pax_values = {
                'pnr': pnr,
                'service_charges': pnr_data,
                'pax_type': pax_type,
                'pax_count': 1,
                'base_fare_ori': float(base_fare_ori),
                'base_tax_ori': float(base_tax_ori),
                'base_price_ori': float(base_price_ori),
                'base_upsell_ori': float(base_upsell_ori),
                'base_upsell_adj': float(base_upsell_adj),
                'base_discount_ori': float(base_discount_ori),
                'base_price': float(base_price),
                'base_commission_vendor': float(base_commission_vendor),
                'base_vendor_vat': float(base_vendor_vat),
                'base_nta_vendor': float(base_nta_vendor),  #
                'base_fare': float(base_fare),
                'base_tax': float(base_tax),
                'base_upsell': float(base_upsell),
                'base_discount': float(base_discount),
                'base_fee_ho': float(base_fee_ho),
                'base_vat_ho': float(base_vat_ho),
                'base_commission': float(base_agent_commission),
                'base_commission_ori': float(base_agent_commission_ori),
                'base_commission_charge': float(base_agent_commission_charge),
                'base_nta': float(base_nta),
                'base_commission_ho': float(base_commission_ho),  #
                'base_hidden_fee_ho': float(base_hidden_fee_ho),
                'base_hidden_vat_ho': float(base_hidden_vat_ho),
                'base_hidden_commission_ho': float(base_hidden_commission_ho),
                'base_commission_ho_ori': float(base_commission_ho_ori),  #
            }
            result.append(pax_values)
        return result

    # TODO: ganti ke get_booking default
    def get_booking_result(self, resv_id, context=False):
        try:
            if isinstance(resv_id, int):
                resv_obj = self.env['tt.reservation.hotel'].browse(resv_id)
            else:
                resv_obj = self.env['tt.reservation.hotel'].search([('name', '=ilike', resv_id)], limit=1)
            if not resv_obj:
                return 'Not Found'
            else:
                resv_obj = resv_obj[0]
            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                raise RequestException(1008)
            # if resv_obj.agent_id.id == context.get('co_agent_id', -1) or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids or resv_obj.agent_type_id.name == self.env.ref('tt_base.agent_b2c').agent_type_id.name or resv_obj.user_id.login == self.env.ref('tt_base.agent_b2c_user').login:
            # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
            _co_user = self.env['res.users'].sudo().browse(int(context['co_uid']))
            if resv_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_system'):
                rooms = self.sudo().prepare_booking_room(resv_obj.room_detail_ids, resv_obj.passenger_ids)
                passengers = self.sudo().prepare_passengers(resv_obj.passenger_ids)
                bookers = self.sudo().prepare_bookers(resv_obj.booker_id)

                passengers[0]['sale_service_charges'] = self.sudo().prepare_service_charge(resv_obj.sale_service_charge_ids, resv_obj.pnr or resv_obj.name)
                if len(resv_obj.passenger_ids[0].channel_service_charge_ids.ids) > 0: ##ASUMSI UPSELL HANYA 1 PER PASSENGER & HOTEL UPSELL PER RESERVASI (MASUK KE PAX 1)
                    svc_csc = self.sudo().prepare_service_charge(resv_obj.passenger_ids[0].channel_service_charge_ids, resv_obj.pnr or resv_obj.name)
                    for pnr in svc_csc:
                        passengers[0]['channel_service_charges'] = {
                            "amount": svc_csc[pnr]['CSC']['amount'],
                            "currency": svc_csc[pnr]['CSC']['currency']
                        }
                passengers[0]['service_charge_details'] = self.sudo().prepare_service_charge_detils(resv_obj.sale_service_charge_ids, resv_obj.pnr or resv_obj.name)
                provider_bookings = []
                for provider_booking in resv_obj.provider_booking_ids:
                    provider_bookings.append(provider_booking.to_dict())
                new_vals = resv_obj.to_dict(context)
                for a in ['arrival_date', 'departure_date']:
                    new_vals.pop(a)
                new_vals.update({
                    "state_description": dict(self.env['tt.reservation.hotel']._fields['state'].selection).get(resv_obj.state),
                    "room_count": resv_obj.room_count,
                    "checkin_date": str(resv_obj.checkin_date),
                    "checkout_date": str(resv_obj.checkout_date),
                    # "provider_type": "hotel",
                    'passengers': passengers,
                    'hotel_name': resv_obj.hotel_name,
                    'hotel_address': resv_obj.hotel_address,
                    'hotel_phone': resv_obj.hotel_phone,
                    'hotel_city_name': resv_obj.hotel_city,
                    'hotel_rating': 0,
                    'images': [],
                    'cancellation_policy': [],
                    'lat': '',
                    'long': '',
                    'hotel_rooms': rooms,
                    'sid_booked': resv_obj.sid_booked,
                    'uid_booked': self.sudo().env.ref('tt_base.agent_b2c_user').id,
                    'uname_booked': self.sudo().env.ref('tt_base.agent_b2c_user').name,
                    'cancellation_policy_str': resv_obj.cancellation_policy_str,
                    'special_request': resv_obj.special_req,
                    'currency': resv_obj.currency_id.name,
                    'provider_bookings': provider_bookings,
                    'total': resv_obj.total,
                })
            else:
                raise RequestException(1035)
            return ERR.get_no_error(new_vals)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    @api.multi
    def get_booking_dummy(self):
        last = self.env['tt.reservation.hotel'].search([('state', '=', 'issued')], limit=1)
        self.get_booking_result(last.id)

    def get_hotel_autocomplete(self, dest_name):
        a = []
        hotel_objs = self.env['tt.hotel'].sudo().search([('name', 'ilike', dest_name)])
        for hotel_obj in hotel_objs:
            json_hotel = {
                'hotel_id': hotel_obj.id,
                'hotel_name': hotel_obj.name
            }
            a.append(json_hotel)
        # return list of dict city_id, city_name
        return a

    def get_destination_autocomplete(self, dest_name):
        a = []
        hotel_objs = self.env['tt.hotel'].sudo().search([('name', 'ilike', dest_name), ('state', '=', 'confirm')])
        for hotel_obj in hotel_objs:
            json_hotel = {
                'id': hotel_obj.id,
                'name': hotel_obj.name,
                'display': hotel_obj.name + ', ' + hotel_obj.city_id.name + ', ' + hotel_obj.country_id.name,
                'type': 'hotel',
                'subtype': hotel_obj.hotel_type_id.name,
            }
            a.append(json_hotel)

        city_objs = self.env['res.city'].sudo().search([('name', 'ilike', dest_name)])
        for city_obj in city_objs:
            json_hotel = {
                'id': city_obj.id,
                'name': city_obj.name,
                'display': city_obj.name + ', ' + city_obj.state_id.name + ', ' + city_obj.country_id.name,
                'type': 'destination',
                'subtype': 'city',
            }
            a.append(json_hotel)

        district_objs = self.env['res.country.district'].sudo().search([('name', 'ilike', dest_name)])
        for district_obj in district_objs:
            json_hotel = {
                'id': district_obj.id,
                'name': district_obj.name,
                'display': district_obj.name + ', ' + district_obj.city_id.name + ', ' + district_obj.country_id.name,
                'type': 'destination',
                'subtype': 'district',
            }
            a.append(json_hotel)
        return a

    def get_hotel_meal_type(self, meal_code, provider_name=''):
        return self.env['tt.meal.type'].sudo().search([('code','=',meal_code)]).name

    def provider_basic_price_rule(self, provider_code, nominal=0):
        service = self.env['tt.service.charge']
        a = 0
        b = 0
        channel_price_rule = service.sudo().get_agent_provider_charge_rule1(provider_code)
        sale_price_rule = service.sudo().get_provider_increment_charge_rule2(provider_code)
        if channel_price_rule:
            a = service.browse(channel_price_rule).count_sale_nominal(nominal)
        if sale_price_rule:
            b = service.browse(sale_price_rule).count_sale_nominal(nominal)
        return b+a,b

    def get_provider_for_dest_name(self, dest_name):
        country = self.env['res.city'].search([('name', '=ilike', dest_name)], limit=1)
        return country and country[0].id or False

    def get_provider_code_alias_api(self, limit):
        resp = {}
        for rec in self.env['tt.provider'].search([('active','=',True), ('alias','!=',False), ('provider_type_id', '=', self.env.ref('tt_reservation_hotel.tt_provider_type_hotel').id)], limit=limit):
            if not resp.get(rec.alias):
                resp[rec.alias] = []
            resp[rec.alias].append(rec.code)
        return resp

    def fail_booking_hotel(self, book_id, msg):
        resv_obj = self.env['tt.reservation.hotel'].search([('name','=',book_id)], limit=1)[0]
        return resv_obj.sudo().action_failed(msg)

    def action_done_hotel_api(self, book_id, issued_res, acq_id, co_uid, context):
        resv_obj = self.env['tt.reservation.hotel'].search([('name','=',book_id)], limit=1)[0]
        resv_obj.sid_issued = context['signature']
        resv_obj.issued_uid = context['co_uid']

        if acq_id:
            self.payment_hotel({
                'book_id': resv_obj.id,
                'member': acq_id['member'],
                'acquirer_seq_id': acq_id['acquirer_seq_id'],
            }, context)

        # Matikan Part ini agar csc tidka tercatat di resv ny juga START
        # for pax in resv_obj.passenger_ids:
        #     for csc in pax.channel_service_charge_ids:
        #         csc.resv_hotel_id = resv_obj.id
        #         csc.total = csc.amount * csc.pax_count
        #         resv_obj.total += csc.total
        # Mtikan Part ini END
        # if resv_obj.state not in ['issued', 'fail_issued']:
        #     resv_obj.sudo().action_issued(acq_id, co_uid)
        return resv_obj.sudo().action_done(issued_res)

    # Asumsi Destinasi sdah berupa kode negara
    def get_provider_for_destination(self, dest_id):
        def provider_to_dic(vendor, city_id):
            def price_to_dic(price_rule):
                vals = {
                    'sequence': price_rule.sequence,
                    'min_price': price_rule.min_price,
                    'max_price': price_rule.max_price,
                    'start_date': price_rule.start_date,
                    'end_date': price_rule.end_date,
                    'amount': price_rule.amount,
                    'percentage': price_rule.percentage,
                }
                return vals

            def vendor_rate_to_dic(recs):
                vals = {}
                for rec in recs:
                    vals[rec.currency_id.name] = rec.sell_rate
                return vals

            resp = city_id.get_city_country_provider_code(city_id.id, vendor.provider_id.provider_code)
            vals = {
                # 'provider_id': vendor.provider_id.id,
                # 'name': vendor.provider_id.name,
                'provider': vendor.provider_id.code or vendor.provider_id.name.lower(),
                'provider_city_id': resp['city_id'],
                'provider_country_id': resp['country_id'],
                'currency_rule': vendor_rate_to_dic(vendor.provider_id.rate_ids),
            }
            return vals

        city_id = self.env['res.city'].browse(dest_id)
        country_id = city_id.state_id and city_id.state_id.country_id or city_id.country_id
        vendor_ids = self.env['tt.provider.destination'].sudo().search([('country_id', '=', country_id.id)])
        providers = [provider_to_dic(rec, city_id) for rec in vendor_ids]

        return providers

    def get_provider_for_destination_dest_name_2(self, dest_name):
        def provider_to_dic(vendor, city_id):
            def vendor_rate_to_dic(recs):
                # vals = {
                #     'currency_id': price_rule.currency_id.code,
                #     'orig_currency_id': price_rule.orig_currency_id.code,
                #     'date': price_rule.date,
                #     'sell_rate': price_rule.sell_rate,
                # }
                vals = {}
                for rec in recs:
                    vals[rec.currency_id.name] = rec.sell_rate
                return vals

            resp = city_id.get_city_country_provider_code(city_id.id, vendor.provider_id.code)
            if vendor.provider_id.active:
                vals = {
                    'provider_id': vendor.provider_id.id,
                    'name': vendor.provider_id.name,
                    'provider': vendor.provider_id.code or vendor.provider_id.name.lower(),
                    'provider_city_id': resp['city_id'],
                    'provider_country_id': resp['country_id'],
                    'currency_rule': vendor_rate_to_dic(vendor.provider_id.rate_ids),
                }
                return vals
            return False

        # Cari di destination

        # Jika tidak ada baru cari di city dan country
        # Flow lama
        providers = []

        city_id = self.env['res.city'].find_city_by_name(dest_name, 1)
        if city_id:
            country_id = city_id.state_id and city_id.state_id.country_id or city_id.country_id

            vendor_ids = self.env['tt.provider.destination'].sudo().search([('country_id', '=', country_id.id), ('is_apply', '=', True)])
            for rec in vendor_ids:
                a = provider_to_dic(rec, city_id)
                if a:
                    providers.append(a)

        # BTBO2: jika data city / alias antara BTBO2 dengan master berbeda
        # mekanisme ini perlu supaya bisa search all autocomplete dari master tnpa perlu sync data city
        prov_rdx_hotel_obj = self.env.ref('tt_reservation_hotel.tt_hotel_provider_rodextrip_hotel')
        if prov_rdx_hotel_obj.active and city_id:
            new_provider = []
            for x in providers:
                if x['provider_id'] != prov_rdx_hotel_obj.id:
                    new_provider.append(x)
            providers.append({
                    'provider_id': prov_rdx_hotel_obj.id,
                    'name': prov_rdx_hotel_obj.name,
                    'provider': prov_rdx_hotel_obj.code or prov_rdx_hotel_obj.name.lower(),
                    'provider_city_id': dest_name.upper(),
                    'provider_country_id': False,
                    'currency_rule': {},
                })

        # Temporary only
        prov_traveloka_obj = self.env.ref('tt_reservation_hotel.tt_hotel_provider_traveloka')
        prov_city_obj = self.env['tt.provider.code'].search([('provider_id','=',prov_traveloka_obj.id),('name','=ilike',dest_name)],limit=1)
        if prov_traveloka_obj.active and city_id:
            new_provider = []
            for x in providers:
                if x['provider_id'] != prov_traveloka_obj.id:
                    new_provider.append(x)
            providers = new_provider
            providers.append({
                'provider_id': prov_traveloka_obj.id,
                'name': prov_traveloka_obj.name,
                'provider': prov_traveloka_obj.code or prov_traveloka_obj.name.lower(),
                'provider_city_id': prov_city_obj and prov_city_obj.code or False,
                'provider_country_id': False,
                'currency_rule': {},
            })
        return providers

    def get_provider_for_destination_dest_name(self, dest_name, context):
        def provider_to_dic(provider_id, city_id):
            def vendor_rate_to_dic(recs):
                # vals = {
                #     'currency_id': price_rule.currency_id.code,
                #     'orig_currency_id': price_rule.orig_currency_id.code,
                #     'date': price_rule.date,
                #     'sell_rate': price_rule.sell_rate,
                # }
                vals = {}
                for rec in recs:
                    vals[rec.currency_id.name] = rec.sell_rate
                return vals

            resp = city_id and city_id.get_city_country_provider_code(city_id.id, provider_id.provider_id.code) or {'city_id': False, 'country_id': False}
            if provider_id.active:
                if provider_id.provider_id.id == self.env.ref('tt_reservation_hotel.tt_hotel_provider_rodextrip_hotel').id:
                    resp['city_id'] = dest_name.upper()
                vals = {
                    'provider_id': provider_id.provider_id.id,
                    'name': provider_id.provider_id.name,
                    'provider': provider_id.provider_id.code or provider_id.provider_id.name.lower(),
                    'provider_city_id': resp['city_id'],
                    'provider_country_id': resp['country_id'],
                    # 'currency_rule': vendor_rate_to_dic(provider_id.rate_ids),
                    'currency_rule': [],
                }
                return vals
            return False

        providers = []
        full_dest_name = dest_name.split(';')
        dest_name = full_dest_name[0]
        country_name = full_dest_name[-1] if len(full_dest_name) > 1 else ''

        city_id = self.env['res.city'].find_city_by_name(dest_name, 1)

        hotel_type_obj = self.env.ref('tt_reservation_hotel.tt_provider_type_hotel')

        # Part untuk tentukan vendor "A" cman di negara yg di mau
        if self.env['ir.config_parameter'].sudo().get_param('hotel.search.use.country.allowed') in ['1',1,'true','True']:
            provider_ids = self.env['tt.provider'].search([('provider_type_id', '=', hotel_type_obj.id), ('alias', '!=', False)])
            vendor_ids = self.env['tt.provider.ho.data'].search([('provider_id', 'in', provider_ids.ids), ('ho_id', '=', context['co_ho_id']), ('provider_destination_ids', '=', False)])
            # prov_dest_ids = self.env['tt.provider.destination'].sudo().search([('country_id', '=', city_id.country_id.id), ('is_apply', '=', True)])
            vendor_ids = [rec for rec in vendor_ids]
            # vendor_ids += [rec.provider_id for rec in prov_dest_ids if rec if rec.provider_id.name]
        else:
            vendor_ids = self.env['tt.provider.ho.data'].search([('provider_type_id', '=', hotel_type_obj.id), ('alias', '!=', False), ('ho_id', '=', context['co_ho_id'])])

        for rec in vendor_ids:
            a = provider_to_dic(rec, city_id)
            if a:
                providers.append(a)
        return providers

    def get_hotel_by_city(self, provider_code, dest_id):
        try:
            city_id = self.env['res.city'].browse(dest_id)
            list_vals = []
            for rec in city_id.sudo().hotel_ids:
                if rec.state == 'confirm':
                    list_vals.append(rec.id)
            return self.get_provider_hotel_detail(list_vals, provider_code)
        except:
            return []

    def get_hotel_by_city_provider(self, provider_code, dest_id):
        try:
            list_vals = []
            city_id = self.env['res.city'].browse(dest_id)
            provider = self.env['tt.provider'].search([('code', '=', provider_code)], limit=1)
            if provider:
                # for rec in city_id.sudo().hotel_ids:
                #     if filter(lambda x: x.provider_id.id == provider.id, rec.provider_hotel_ids):
                #         list_vals.append(rec.id)
                # return self.get_provider_hotel_detail(list_vals, provider.id)

                for rec in city_id.sudo().hotel_ids:
                    a = list(filter(lambda x: x.provider_id.id == provider.id, rec.provider_hotel_ids))
                    a and list_vals.append(a[0].code)
                return list_vals
            else:
                return []
        except:
            return []

    def update_booking_line(self, booking_code, issued_code, room_id):
        line_obj = self.env['tt.hotel.reservation.details'].sudo().browse(int(room_id))
        line_obj.name = booking_code
        line_obj.issued_name = issued_code
        return True

    def get_record_by_string(self, search_str, dest_id):
        if dest_id:
            hotel_ids = self.env['res.city'].sudo().browse(int(dest_id)).hotel_ids[:10] # Test; Non test remove[:10]
            return {
                'hotel_ids': self.get_provider_hotel_detail(hotel_ids.ids,''),
                'city_ids': [],
                'country_ids': [],
                'landmark_ids': []
            }
        else:
            return {
                'hotel_ids': self.get_provider_hotel_detail(self.env['tt.hotel'].sudo().search([('name', 'ilike', search_str), ('state', '=', 'confirm')]).ids, ''),
                'city_ids': [self.get_provider_city_detail(rec) for rec in self.env['res.city'].sudo().search([('name', 'ilike', search_str)])],
                'country_ids': self.prepare_countries(self.env['res.country'].sudo().search([('name', 'ilike', search_str)])),
                'landmark_ids': self.prepare_landmark(self.env['tt.landmark'].sudo().search([('name', 'ilike', search_str)]))
            }

    def get_record_by_string_limited(self, search_str, dest_id, limit, offset):
        if dest_id:
            hotel_ids = self.env['res.city'].sudo().browse(int(dest_id)).hotel_ids[:10] # Test; Non test remove[:10]
            return {
                'hotel_ids': self.get_provider_hotel_detail(hotel_ids.ids,''),
                'city_ids': [],
                'country_ids': [],
                'landmark_ids': []
            }
        else:
            return {
                'hotel_ids': self.get_provider_hotel_detail(self.env['tt.hotel'].sudo().search([('name', 'ilike', search_str), ('state', '=', 'confirm')], limit=limit, offset=offset).ids, ''),
                'city_ids': [self.get_provider_city_detail(rec) for rec in self.env['res.city'].sudo().search([('name', 'ilike', search_str)], limit=limit, offset=offset)],
                'country_ids': [],
                'landmark_ids': self.prepare_landmark(self.env['tt.landmark'].sudo().search([('name', 'ilike', search_str)], limit=limit, offset=offset))
            }

    def get_top_facility(self, limit):
        return [{'facility_name': facility.name, 'sequence': facility.sequence,
                 'image_url': facility.image_url, 'image_url2': facility.image_url2, 'internal_name': ','.join(rec.code for rec in facility.facility_id.provider_ids),} for
                facility in self.env['tt.hotel.top.facility'].search([], limit=limit)]

    def get_facility_img(self, limit=99):
        return [{'facility_id': facility.id, 'facility_name': facility.name, 'internal_code': facility.internal_code, 'facility_image': facility.image_url3, }
                for facility in self.env['tt.hotel.facility'].search([], limit=limit)]


class TestSearchLine(models.Model):
    _name = 'test.search.line'
    _description = 'Test Search Line'

    name = fields.Char('name')
    reservation_id = fields.Many2one('test.search', 'Reservation No')
    sale_price = fields.Monetary('Sale Price')
    qty = fields.Integer('Qty')
    currency_id = fields.Many2one('res.currency', 'Currency')
    special_request = fields.Text('Special request')
    sequence = fields.Integer('Sequence')
    subtotal_price = fields.Monetary('Total')
    is_fixed = fields.Boolean('Fixed Price', default=False)
    max_qty = fields.Integer('Maximum Quantity', default=1)

    @api.depends('sale_price', 'qty')
    def calc(self):
        self.subtotal_price = self.qty * self.sale_price

    @api.onchange('sale_price', 'qty')
    def onchange_calc_sub(self):
        if self.qty < self.max_qty:
            self.subtotal_price = self.qty * self.sale_price
        else:
            self.qty = self.max_qty
            self.subtotal_price = self.qty * self.sale_price
            # raise UserError(_("Ordered qty cannot more than maximum qty"))


class TestSearchLine2(models.Model):
    _name = 'test.search.line2'
    _inherit = 'test.search.line'


class TestSearchWizard(models.TransientModel):
    _name = 'test.search.wizard'
    _description = 'Test Search Wizard'

    name = fields.Char('City / Hotel Name')
    rate_id = fields.Many2one('tt.room.rate', 'Room')
    hotel_id = fields.Many2one('tt.hotel', 'Hotel', related='rate_id.room_info_id.hotel_id')
    room_info_id = fields.Many2one('tt.room.info', 'Room Info', related='rate_id.room_info_id')
    date_start = fields.Date('Date Start', default=fields.Date.context_today)
    date_end = fields.Date('Date End', default=fields.Date.context_today)
    nights = fields.Integer('Nights')
    room = fields.Integer('Room')
    guest = fields.Integer('Guest')

    @api.one
    def search_hotel(self):
        # Todo Search By City Name
        # self.env['tt.hotel'].search([('name', 'ilike', self.name)])
        # hotels = self.env['tt.hotel'].search([('name', 'ilike', self.name)])

        # action = self.env.ref('stock.action_picking_tree')
        # result = action.read()[0]
        # result['context'] = {}
        # pick_ids = sum([order.picking_ids.ids for order in self], [])
        # result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        # return result

        vals = {
            'name': self.rate_id.room_info_id.name + ' ' + self.date_start,
            'rate_id': self.rate_id.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'nights': self.nights,
            'guest': self.guest,
        }
        search_id = self.env['test.search'].create(vals)

        vals = {
            'name': self.rate_id.room_info_id.name,
            'sale_price': self.rate_id.sale_price,
            'qty': 1,
            'reservation_id': search_id.id,
            'sequence': 10,
            'subtotal_price': self.rate_id.sale_price,
        }
        self.env['test.search.line'].create(vals)

        rule_ids = self.env['tt.service.charge'].search_rate_for_thisday(self.rate_id)
        for rule in rule_ids:
            rule_obj = self.env['tt.service.charge'].browse(rule)
            qty = rule_obj['calculate_var'] == 'once' and 1 or False
            vals = {
                'name': rule_obj['name'],
                'sale_price': rule_obj['type'] == 'fix' and rule_obj['sale_nominal'] or rule_obj['sale_nominal'] * self.rate_id.sale_price / 100,
                'qty': qty,
                'reservation_id': search_id.id,
                'sequence': rule_obj.sequence,
                # 'subtotal_price': rule_obj['sale_nominal'] * qty,
            }
            self.env['test.search.line'].create(vals)
