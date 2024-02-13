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
    # Notes: Ambil data dari vendor (Country, Meal type, Facility, City + destination, Hotel, Other Info)
    # Notes: Simpan ke table masing2x masukan sisane ke other
    # Notes: cara
    # Todo: Perlu catat source data ne
    # Todo: Prepare Cron tiap provider
    def v2_collect_by_system_itank(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_itank').id

        rendered_city = []
        API_CN_HOTEL.signin()

        country_ids = self.env['res.country'].search([('code','!=',False)])
        for target_city_obj in country_ids:
            target_city_name = target_city_obj.code
            if target_city_name in rendered_city:
                continue
            response = API_CN_HOTEL.get_record_by_api({'type': 'hotel', 'provider': 'itank', 'codes': target_city_name})

            file_loc = base_cache_directory + 'itank/' + target_city_obj.city_id.country_id.name
            if not os.path.exists(file_loc):
                os.makedirs(file_loc)

            if response['response']['result']:
                name = file_loc + '/' + target_city_name + ".json"
                file = open(name, 'w')
                file.write(json.dumps(response['response']['result'][0]))
                file.close()
                rendered_city.append(target_city_name)

            self.env['ir.config_parameter'].sudo().set_param('hotel.city.rendered.list', json.dumps(rendered_city))
            self.env.cr.commit()
        self.env['ir.config_parameter'].sudo().set_param('hotel.city.rendered.list', json.dumps([]))
        _logger.info("===== Done =====")
        return True

    def provider_code_to_dict(self, provider_code_objs):
        result = {}
        for rec in provider_code_objs:
            if rec.res_model == 'tt.hotel.destination':
                obj = self.env['tt.hotel.destination'].browse(rec.res_id)
                result[rec.code] = [rec.name, obj.country_id.name]
            else:
                result[rec.code] = rec.name
        return result

    # 1b. Collect by Human / File excel
    # Compiller: Master / Local
    # Notes: Ambil data dari vendor yg dikasih manual atau tidak bisa diakses melalui API
    # Notes: Mesti bantuan human untuk upload file location serta formating
    # Notes: Bagian ini bakal sering berubah
    def v2_collect_by_human_itank(self):
        return True

    def v2_collect_by_human_csv_itank(self):
        return True

    # 1c. Get Country Code
    def v2_get_country_code_itank(self):
        base_cache_directory = self.env['ir.config_parameter'].sudo().get_param('hotel.cache.directory')
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_itank').id
        cache_hotel = {}
        type = {}

        API_CN_HOTEL.signin()
        country_ids = self.env['res.country'].search([('code', '!=', False)], limit=1)
        response = API_CN_HOTEL.get_record_by_api({'type': 'country', 'provider': 'itank', 'codes': country_ids[0].code})

        for val in response['response']['result'][0]:
            _logger.info("=== Processing (" + val['code'] + ") ===")

            country_obj = self.env['res.country'].search([('code', '=ilike', val['code'])], limit=1)  # By Code
            country_obj = country_obj and country_obj[0] or self.env['res.country'].create({'name': val['name'], 'code': val['code']})

            # Create external ID:
            if not self.env['tt.provider.code'].search([('res_model', '=', 'res.country'), ('res_id', '=', country_obj.id), ('code', '=', val), ('provider_id', '=', provider_id)]):
                self.env['tt.provider.code'].create({
                    'res_model': 'res.country',
                    'res_id': country_obj.id,
                    'name': val['name'],
                    'code': val['code'],
                    'provider_id': provider_id,
                })
        return True

    # 1d. Get City Code
    def v2_get_city_code_itank(self):
        model = 'res.city'
        model1 = 'tt.hotel.destination'

        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_itank').id
        codes = self.env['tt.provider.code'].search([('res_model', '=', 'res.country'), ('provider_id', '=', provider_id)])
        codes = [x.code + '~' + x.name for x in codes]

        response = API_CN_HOTEL.get_record_by_api({'type': 'city', 'provider': 'itank', 'codes': codes})
        params = self.env['ir.config_parameter'].sudo().get_param('hotel.city.rendered.list')
        rendered_country = json.loads(params)

        for key in response['response']['result']:
            if key.split('~')[0] in rendered_country:
                _logger.info("===== Skip " + key +" =====")
                continue
            country_obj = self.env['res.country'].search([('code', '=', key.split('~')[0])], limit=1)
            idx = 0
            for city in response['response']['result'][key]:
                if self.env['tt.provider.code'].search([('code', '=', key.split('~')[0] + '~' + city['code']), ('provider_id', '=', provider_id)]):
                    _logger.info('Skip ' + city['name'] + ' with code ' + key.split('~')[0] + '~' + city['code'])
                    continue
                city_obj = self.env[model].find_city_by_name(city['name'].split(',')[0], 1, country_obj.id)  # By Code

                # Create external ID:
                if city_obj:
                    self.env['tt.provider.code'].create({
                        'res_model': model,
                        'res_id': city_obj.id,
                        'city_id': city_obj.id,
                        'name': city['name'] + '; ' + country_obj.name,
                        'code': key.split('~')[0] + '~' + city['code'],
                        'provider_id': provider_id,
                    })
                else:
                    is_exact, res_obj = self.env[model1].find_similar_obj({
                        'id': False,
                        'name': city['name'] + '; ' + country_obj.name,
                        'city_str': city['name'],
                        'city_id': city_obj and city_obj.id or False,
                        'state_str': False,
                        'state_id': False,
                        'country_str': key.split('~')[1],
                        'country_id': country_obj.id,
                    })
                    self.env['tt.provider.code'].create({
                        'res_model': model1,
                        'res_id': res_obj.id,
                        'name': city['name'] + '; ' + country_obj.name,
                        'code': key.split('~')[0] + '~' + city['code'],
                        'provider_id': provider_id,
                    })
                _logger.info('Render ' + city['name'] + '; ' + country_obj.name + ' END')
                idx += 1

                if idx % 25 == 0:
                    self.env.cr.commit()
                    _logger.info('Commit ....')

            rendered_country.append(key.split('~')[0])
            self.env.cr.commit()
            self.env['ir.config_parameter'].sudo().set_param('hotel.city.rendered.list', json.dumps(rendered_country))
        _logger.info("===== itank City Done =====")
        return True

    # 1e. Get Meal Code
    def v2_get_meal_code_itank(self):
        provider_id = self.env.ref('tt_reservation_hotel.tt_hotel_provider_itank').id
        codes = self.env['tt.provider.code'].search([('res_model', 'in', ['res.city','tt.hotel.destination']), ('provider_id', '=', provider_id)])
        codes.unlink()
        return True

    # 1f. Get Room Type Code
    def v2_get_room_code_itank(self):
        return True

    # 1g. Get Facility Code
    def v2_get_facility_code_itank(self):
        return True
