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
    def v2_collect_by_system_miki(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
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
            hotel_list = {}
            for obj in res.get('response'):
                if obj.get('code'):
                    rec = self.env['res.city'].find_city_by_name(obj['addressinfo'].get('city', ''))
                    city_id = rec.city_id
                    value = {
                        'id': obj['code'],
                        'name': obj.get('basicinfo') and obj.get('basicinfo').get('name') or '',
                        'street': obj.get('addressinfo') and obj['addressinfo'].get('address1') or '',
                        'street2': obj.get('addressinfo') and 'City: ' + obj['addressinfo'].get('city`', ' ') + '; State: ' + obj['addressinfo'].get('state', ' ') or '',
                        'street3': obj['addressinfo'].get('country') or city_id.country_id.name,
                        'description': obj.get('locationinfo') and 'Raildistance: ' +
                                       obj['locationinfo'].get('raildistance', ' ') + '; Airport Distance: ' +
                                       obj['locationinfo'].get('airportdistance', ' ') or '',
                        'email': obj.get('contactinfo') and obj.get('contactinfo').get('email') or '',
                        'images': [(6, 0, self.rec_to_images(obj.get('images')))],
                        'facilities': [],
                        'phone': obj.get('contactinfo') and obj.get('contactinfo').get('telephonenumber1') or '',
                        'fax': obj.get('contactinfo') and obj.get('contactinfo').get('faxnumber') or '',
                        'zip': obj.get('addressinfo') and obj['addressinfo'].get('zipcode'),
                        'website': obj.get('web'),
                        'lat': obj.get('coordinates') and str(obj.get('coordinates').get('latitude')),
                        'long': obj.get('coordinates') and str(obj.get('coordinates').get('longitude')),
                        'rating': obj.get('categoryCode') and int(obj.get('categoryCode')[0]),
                        'city': city_id and city_id[0].id or False
                    }
                    if not hotel_list.get(city_id.country_id.name):
                        hotel_list[city_id.country_id.name] = {}
                    if not hotel_list[city_id.country_id.name].get(city_id):
                        hotel_list[city_id.country_id.name][city_id] = []
                    hotel_list[city_id.country_id.name][city_id].append(value)

            for country in hotel_list.keys():
                txt_country = country.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')',                                                               '')
                filename = base_cache_directory + "miki_api/" + txt_country
                if not os.path.exists(filename):
                    os.mkdir(filename)
                for city in hotel_list[country].keys():
                    txt_city = city.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')', '')
                    _logger.info("Write File " + txt_country + " City: " + txt_city)
                    filename1 = filename + "/" + txt_city + ".json"
                    file = open(filename1, 'w')
                    file.write(json.dumps(hotel_list[country][city]))
                    file.close()
                self.env.cr.commit()
        _logger.info("===== Done =====")

    # Human harus FTP untuk ambil XML ini
    # Tipe data XML
    # URL: ftp://ftp.mikinet.co.uk
    # Pass: USER PASS ambil di Document vendor
    def v2_collect_by_human_miki_xml(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        file_ids = glob.glob(base_cache_directory + "miki_api/master/*.xml")
        file_ids.sort()
        country_ids = {}
        for file_name in file_ids:
            _logger.info("Read " + file_name)
            try:
                file = open(file_name, 'r')
                hotel_list = file.read()
                file.close()
            except:
                continue
            try:
                for hotel in isinstance(xmltodict.parse(hotel_list)['productInfoResponse']['productInfo']['product'], list) and xmltodict.parse(hotel_list)['productInfoResponse']['productInfo']['product'] or [xmltodict.parse(hotel_list)['productInfoResponse']['productInfo']['product'],]:
                    # if hotel['productDescription']['productName'].title() == 'Achat Comfort':
                    #     pass
                    imgs = hotel['hotelProductInfo'].get('images') and hotel['hotelProductInfo']['images']['image'] or []
                    hotel_fmt = {
                        'id': hotel['productCode']['#text'],
                        'name': hotel['productDescription']['productName'].title(),
                        'street': hotel['hotelProductInfo']['contactInfo']['address'].get('street1'),
                        'street2': '',
                        'street3': hotel['hotelProductInfo']['contactInfo']['address'].get('street2',''),
                        'description': hotel['productDescription']['productDetailText'],
                        'email': hotel['hotelProductInfo']['contactInfo'].get('email'),
                        'images': imgs and [{'name': img['@imageCaption'], 'url': img['@imageURL']} for img in isinstance(imgs, list) and imgs or [imgs]] or [],
                        'facilities': [key for (key, value) in hotel['hotelProductInfo']['hotelFacilities'].items() if value == 'true'] + [key for (key, value) in hotel['hotelProductInfo']['hotelRoomFacilities'].items() if value == 'true'],
                        'phone': hotel['hotelProductInfo']['contactInfo'].get('telephoneNumber'),
                        'fax': hotel['hotelProductInfo']['contactInfo'].get('faxNumber'),
                        'zip': hotel['hotelProductInfo']['contactInfo']['address'].get('street3'),
                        'website': '',
                        'lat': '',
                        'long': '',
                        'rating': hotel['hotelProductInfo']['hotelInfo'].get('starRating') or '',
                        'hotel_type': '',
                        'city': hotel['hotelProductInfo']['contactInfo']['address'].get('city', '').title(),
                        'country': hotel['hotelProductInfo']['contactInfo']['address'].get('country') or '',
                    }
                    _logger.info("Adding Hotel:" + hotel_fmt['name'] + ' in City: ' + hotel_fmt['city'])
                    if not country_ids.get(hotel_fmt['country']):
                        country_ids[hotel_fmt['country']] = {}
                    if not country_ids[hotel_fmt['country']].get(hotel_fmt['city']):
                        country_ids[hotel_fmt['country']][hotel_fmt['city']] = []
                    country_ids[hotel_fmt['country']][hotel_fmt['city']].append(hotel_fmt)

            except:
                _logger.info(msg='Error while Processing {}'.format(hotel['productDescription']['productName'],))
                continue
        # Write per City
        need_to_add = [['Name', 'Hotel Qty']]
        for country in country_ids.keys():
            txt_country = country.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')', '')
            filename = base_cache_directory + "miki_api/" + txt_country
            if not os.path.exists(filename):
                os.mkdir(filename)
            for city in country_ids[country].keys():
                txt_city = city.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')', '')
                _logger.info("Write File " + txt_country + " City: " + txt_city)
                filename1 = filename + "/" + txt_city + ".json"
                file = open(filename1, 'w')
                file.write(json.dumps(country_ids[country][city]))
                file.close()
                need_to_add.append([city, len(country_ids[country][city])])
            self.env.cr.commit()
        with open(base_cache_directory + 'miki_api/result/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add)
        csvFile.close()
        _logger.info("===== Done =====")

    # Human harus minta data CSV dari vendor via email/ manual
    def v2_collect_by_human_miki_csv(self):
        hotel_fmt_list = {}
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        # with open(base_cache_directory + 'miki/00_master/Rodex_Des2022_full.csv', 'r') as f: # 17k
        # with open(base_cache_directory + 'miki/00_master/Rodex_jul2023.csv', 'r') as f: #5k
        with open(base_cache_directory + 'miki/00_master/20231126.csv', 'r') as f: #18k
            hotel_ids = csv.reader(f, delimiter=';')
            index = False
            for hotel in hotel_ids:
                if not index:
                    index = 1
                    continue
                else:
                    index += 1
                # Rodex_Des2022_full
                # _logger.info("Processing (" + hotel[5] + ").")
                # hotel_fmt = {
                #     'id': hotel[0],
                #     'name': hotel[5],
                #     'street': hotel[6],
                #     'street2': hotel[8] or '', #Usually ZipCode
                #     'street3': hotel[7] or '', #Usually Citydex
                #     'email': '',
                #     'images': [],
                #     'facilities': [],
                #     'phone': hotel[11],
                #     'fax': hotel[12],
                #     'zip': '',
                #     'website': '',
                #     'lat': hotel[9],
                #     'long': hotel[10],
                #     'rating': 0,
                #     'hotel_type': '',
                #     'country': hotel[3],
                # }

                # Rodex_jul2023
                # hotel_fmt = {
                #                     'id': hotel[0],
                #                     'name': hotel[4],
                #                     'street': hotel[5],
                #                     'street2': hotel[6] or '',  # Usually Citydex
                #                     'street3': hotel[7] or '',  # Usually ZipCode
                #                     'email': '',
                #                     'images': [],
                #                     'facilities': [],
                #                     'phone': hotel[10],
                #                     'fax': hotel[11],
                #                     'zip': '',
                #                     'website': '',
                #                     'lat': hotel[8],
                #                     'long': hotel[9],
                #                     'rating': 0,
                #                     'hotel_type': '',
                #                     'city': hotel[3],
                #                     'country': hotel[2],
                #                     'description': 'Giata Code: ' + str(hotel[1]),
                #                 }
                _logger.info("Processing " + str(index) + ". " + hotel[4])
                hotel_fmt = {
                    'id': hotel[0],
                    'name': hotel[5],
                    'street': hotel[6],
                    'street2': hotel[7] or '',  # Usually Citydex
                    'street3': hotel[8] or '',  # Usually ZipCode
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
                    'city': hotel[4],
                    'country': hotel[3],
                    'description': 'Giata Code: ' + str(hotel[1]),
                }

                # Untuk yg RO (1)
                # hotel_fmt.update({
                #     'description': 'Giata Code: ' + str(hotel[1]),
                #     'city': hotel[4],
                # })
                # Untuk yg 20190703_en.csv
                # hotel_fmt.update({
                #     'description': 'Supplier Code: ' + str(hotel[4]),
                #     'city': hotel[2],
                # })

                if not hotel_fmt_list.get(hotel_fmt['country']):
                    hotel_fmt_list[hotel_fmt['country']] = {}
                if not hotel_fmt_list[hotel_fmt['country']].get(hotel_fmt['city']):
                    hotel_fmt_list[hotel_fmt['country']][hotel_fmt['city']] = []
                hotel_fmt_list[hotel_fmt['country']][hotel_fmt['city']].append(hotel_fmt)

            need_to_add = [['Name', 'Hotel Qty']]
            for country in hotel_fmt_list.keys():
                txt_country = country.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')',                                                               '')
                filename = base_cache_directory + "miki/" + txt_country
                if not os.path.exists(filename):
                    os.mkdir(filename)
                for city in hotel_fmt_list[country].keys():
                    txt_city = city.replace('/', '-').replace('(and vicinity)', '').replace(' (', '-').replace(')', '')
                    # _logger.info("Write File " + txt_country + " City: " + txt_city)
                    filename1 = filename + "/" + txt_city + ".json"
                    file = open(filename1, 'w')
                    file.write(json.dumps(hotel_fmt_list[country][city]))
                    file.close()
                self.env.cr.commit()
                need_to_add.append([city, len(hotel_fmt_list[country][city])])
        f.close()

        with open(base_cache_directory + 'miki/00_master/result_data.csv', 'w') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerows(need_to_add)
        csvFile.close()
        _logger.info("===== Done =====")

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    def v2_collect_by_human_miki(self):
        # self.v2_collect_by_human_miki_xml()
        self.v2_collect_by_human_miki_csv()

    # 1c. Get Country Code
    def v2_get_country_code_miki(self):
        return True

    # 1d. Get City Code save in tt.hotel.destination
    def v2_get_city_code_miki(self):
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_miki(self):
        return True

    # 1f. Get room Code
    def v2_get_room_code_miki(self):
        return True

    # 1g. Get Facility Code
    def v2_get_facility_code_miki(self):
        return True
