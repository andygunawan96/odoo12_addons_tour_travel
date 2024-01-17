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
    def v2_collect_by_system_hotelinx(self):
        return True

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    def v2_collect_by_human_hotelinx(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        last_render = int(self.env['ir.config_parameter'].sudo().get_param('last.gw.render.idx'))
        hotel_fmt_dict = {}
        with open(base_cache_directory + '/hotellinx/00_mster/Hotelinx_MappingFile-231101.csv', 'r') as f:
            city_ids = csv.reader(f, delimiter=',')
            # Mulai dari index 1 (Remove Header)
            # 0 HotelId,
            # 1 HotelName,
            # 2 Description,
            # 3 Latitude,
            # 4 Longitude,
            # 5 Address,
            # 6 Rating,
            # 7 CountryId, 8 CountryName,
            # 9 CityId, 10 CityName,
            # 11 GiataId,
            # 12 HotelFrontImage,
            # 13 IsRecomondedHotel,
            # 14 IsActive,
            # 15 UpdatedDate,
            # 16 EAN,
            # 17 EAN_B2B,
            # 18 EAN_PKG,
            # 19 HotelBedsV1,
            # 20 HotelBedsV1_new,
            # 21 MgBedBank,
            # 22 Traveloka
            for idx, rec in enumerate(city_ids):
                if rec[1] == 'HotelName' or idx <= last_render:
                    continue
                # _logger.info("Processing " + rec[1] + ": (" + rec[10]+ "), " + rec[8])
                hotel_fmt = {
                    'id': rec[0],
                    'name': rec[1],
                    'street': rec[5],
                    'street2': rec[8].upper().replace('/', '-'),
                    'street3': '',
                    'description': rec[2],
                    'email': '',
                    'images': [rec[12]],
                    'facilities': [],
                    'phone': '',
                    'fax': '',
                    'zip': '',
                    'website': '',
                    'lat': rec[3],
                    'long': rec[4],
                    'rating': rec[6] and int(rec[6][0]) or 0,
                    'hotel_type': '',
                    'city': rec[10].replace('/', '-'),

                    'IsActive': rec[14],
                    'GiataId': rec[11],
                    'HotelBedsV1': rec[19],
                    'HotelBedsV1_new': rec[20],
                    'MgBedBank': rec[21],
                    'Traveloka': rec[22],
                }

                if not hotel_fmt_dict.get(hotel_fmt['street2']):
                    hotel_fmt_dict[hotel_fmt['street2']] = {}
                if not hotel_fmt_dict[hotel_fmt['street2']].get(hotel_fmt['city']):
                    hotel_fmt_dict[hotel_fmt['street2']][hotel_fmt['city']] = []
                hotel_fmt_dict[hotel_fmt['street2']][hotel_fmt['city']].append(hotel_fmt)

                if idx % 3000 == 0:
                    base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
                    for country_dt in hotel_fmt_dict.keys():
                        filename = base_cache_directory + "hotellinx/" + country_dt
                        if not os.path.exists(filename):
                            os.mkdir(filename)
                        for city_dt in hotel_fmt_dict[country_dt].keys():
                            filename1 = filename + "/" + city_dt + ".json"
                            try:
                                with open(filename1, 'r') as f2:
                                    file_dt = f2.read()
                                    file_dt = json.loads(file_dt)
                            except:
                                file_dt = []

                            file = open(filename1, 'w')
                            old_id = [x['id'] for x in file_dt]
                            new_dt = [x for x in hotel_fmt_dict[country_dt][city_dt] if x['id'] not in old_id]
                            file.write(json.dumps(new_dt + file_dt))
                            file.close()
                            # _logger.info("Done City: " + city_dt + ' get: ' + str(len(hotel_fmt_dict[country_dt][city_dt])) + ' Hotel(s)')

                    hotel_fmt_dict = {}
                    self.env['ir.config_parameter'].sudo().set_param('last.gw.render.idx', idx)
                    self.env.cr.commit()
                    _logger.info("Write until " + str(idx))

        f.close()

    # 1c. Get Country Code
    def v2_get_country_code_hotelinx(self):
        return True

    # 1d. Get City Code
    def v2_get_city_code_hotelinx(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_hotelinx').id
        render_code = []
        old_obj = self.env['tt.provider.code'].search([('res_model', '=', 'tt.hotel.destination'), ('provider_id', '=', provider_id)])
        old_obj = [x.code for x in old_obj]
        new_code = []
        with open(base_cache_directory + '/hotellinx/00_mster/Hotelinx_MappingFile-231101.csv', 'r') as f:
            city_ids = csv.reader(f, delimiter=',')
            for idx, rec in enumerate(city_ids):
                if rec[1] == 'HotelName' or rec[9] in render_code:
                    continue
                # 9 CityId, 10 CityName,
                code = rec[9]
                # old_obj = self.env['tt.provider.code'].search([('res_model', '=', 'tt.hotel.destination'), ('code', '=', code),('provider_id', '=', provider_id)], limit=1)
                # old_obj = False
                if code not in old_obj and code not in new_code :
                    new_code.append(code)
                    new_dict = {
                        'id': False,
                        'name': rec[10],
                        'city_str': rec[10],
                        'state_str': '',
                        'country_str': rec[8],
                    }
                    is_exact, new_obj = self.env['tt.hotel.destination'].find_similar_obj(new_dict, False)
                    if not is_exact:
                        new_obj = self.env['tt.hotel.destination'].create(new_dict)
                        new_obj.fill_obj_by_str()
                        _logger.info('Create New Destination {} with code {}'.format(rec[10], code))
                    # else:
                        # _logger.info('Destination already Exist for {}, Country {}'.format(rec[10], rec[8]))

                    self.env['tt.provider.code'].create({
                        'res_model': 'tt.hotel.destination',
                        'res_id': new_obj.id,
                        'name': rec[10] + ", " + rec[8],
                        'code': code,
                        'provider_id': provider_id,
                    })
                    render_code.append(rec[9])
                    _logger.info('{}. Create Provider Code for {}'.format(str(idx), rec[10]))
                    if len(render_code) % 100 == 0:
                        self.env.cr.commit()
                # else:
                #     _logger.info('Skipping {} already Exist in {} with id {}'.format(code, old_obj.res_model,str(old_obj.res_id)))

        f.close()
        _logger.info('Render END')
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_hotelinx(self):
        return True

    # 1f. Get Room Type Code
    def v2_get_room_code_hotelinx(self):
        return True

    # 1g. Get Facility Code
    def v2_get_facility_code_hotelinx(self):
        return True
