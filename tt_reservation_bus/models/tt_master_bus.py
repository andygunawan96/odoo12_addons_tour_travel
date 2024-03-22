from odoo import api, fields, models, _
from odoo.http import request
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
import logging, traceback
import json
import base64
import pickle
from datetime import datetime
import csv
import os
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

from ...tools import session
SESSION_NT = session.Session()


class BusStation(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.master.bus.station'
    _description = 'Master Bus Station'

    name = fields.Char('Station Name', readonly=True)
    address = fields.Char('Station Address', readonly=True)
    code = fields.Char('Station Code', readonly=True)
    longitude = fields.Char('Longitude Code', readonly=True)
    latitude = fields.Char('Latitude Code', readonly=True)
    city_id = fields.Many2one('res.city', 'City ID')
    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True)

    bus_journey_ids = fields.Many2many('tt.master.bus.station', 'tt_bus_journey_rel', 'station_id', 'journey_id', string='Bus Journey', readonly=False)
    active = fields.Boolean('Active', default=True)


    def action_bus_sync_data_traveloka(self):
        ## tambah context
        ## kurang test
        ho_id = self.env.user.ho_id.id
        res = self.env['tt.bus.api.con'].sync_data({}, ho_id)
        _logger.info(json.dumps(res))
        #self.env['res.city'].find_city_by_name(rec.city, limit=5)
        if res['error_code'] == 0:
            provider_id = self.env.ref('tt_reservation_bus.tt_provider_bus_traveloka').id
            provider_type_id = self.env.ref('tt_reservation_bus.tt_provider_type_bus').id
            for rec_city in res['response']['city']:
                country_obj = self.env['res.country'].find_country_by_name(rec_city['country_code'], 1)
                country_obj = country_obj and country_obj[0] or self.env['res.country'].create({'name': rec_city['country_code']})

                city_ids = self.env['res.city'].find_city_by_name(rec_city['name'], limit=5, country_id=country_obj.id)
                if not city_ids:
                    self.env['res.city'].create({
                        "name": rec_city['name'],
                        "country_id": country_obj.id
                    })
                    city_ids = self.env['res.city'].find_city_by_name(rec_city['name'], limit=5,country_id=country_obj.id)
                for rec_data_backend_city in city_ids:
                    # if rec_data_backend_city.country_id.code == rec_city['country_code']:
                    for data_provider in rec_data_backend_city.provider_code_ids:
                        if data_provider.provider_id.code == 'tv_bus':
                            # DATA FOUND UPDATE CODE
                            data_provider.update({
                                "code": rec_city['id']
                            })
                            check_data = False
                            break
                    #ASUMSI KALAU ADA TETAPI TIDAK KETEMU
                    self.env['tt.provider.code'].create({
                        'res_model': 'res.city',
                        'res_id': rec_data_backend_city.id,
                        'city_id': rec_data_backend_city.id,
                        'name': rec_city['name'],
                        'code': rec_city['id'],
                        'provider_id': provider_id,
                        'country_id': country_obj.id
                    })

            country_obj = self.env['res.country'].find_country_by_name('ID', 1)
            for rec_station in res['response']['station']:
                city_obj = self.env['res.city'].find_city_by_name(rec_city['name'], limit=1, country_id=country_obj.id) #ASUMSI YG TIDAK ADA SUDAH TER CREATE
                station_obj = self.search([('code','=', rec_station['id'])], limit=1)
                if station_obj:
                    station_obj.update({
                        "name": rec_station['name'],
                        "address": rec_station['address'],
                        "code": rec_station['id'],
                        "longitude": rec_station['long'],
                        "latitude": rec_station['lat'],
                        "city_id": city_obj.id,
                        "provider_id": provider_id
                    })
                else:
                    self.create({
                        "name": rec_station['name'],
                        "address": rec_station['address'],
                        "code": rec_station['id'],
                        "longitude": rec_station['long'],
                        "latitude": rec_station['lat'],
                        "city_id": city_obj.id,
                        "provider_id": provider_id
                    })

    def get_config_api(self):
        res = {
            "station": {},
            "city": {}
        }
        data = self.sudo().search([])
        for rec in data:
            res["station"][rec['code']] = self.get_data_origin(rec)
            for destination in rec.bus_journey_ids:
                res["station"][rec['code']]['destination'].append(self.get_data_destination(destination))

        data = self.env['tt.provider.code'].search([('provider_id.id', '=', self.env.ref('tt_reservation_bus.tt_provider_bus_traveloka').id)])
        for rec in data:
            res['city'][rec.code] = {
                "name": rec.name,
                "provider": rec.provider_id.code
            }
        return ERR.get_no_error(res)

    def get_data_origin(self, data):
        return {
            "name": data.name,
            "address": data.address,
            "longitude": data.longitude,
            "latitude": data.latitude,
            "city": data.city_id.name,
            "provider": data.provider_id.code,
            'destination': []
        }

    def get_data_destination(self, data):
        return data.code

    def action_bus_sync_get_bus_journey_traveloka(self):
        data = self.search([])
        ho_id = self.env.user.ho_id.id
        for rec in data:
            ## tambah context
            ## kurang test
            res = self.env['tt.bus.api.con'].sync_get_data_journey({
                "id": rec.code
            }, ho_id)
            if res['error_code'] == 0:
                data_bus_list = self.search([('code', 'in', res['response']['data'])])
                list_id = []
                for rec_data_bus in data_bus_list:
                    list_id.append(rec_data_bus.id)
                rec.update({
                    "bus_journey_ids": [(6, 0, list_id)]
                })
                self.env.cr.commit()
            _logger.info(json.dumps(res))



class BusSyncData(models.TransientModel):
    _name = "bus.sync.data.wizard"
    _description = 'Bus Sync Data Wizard'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_bus.tt_provider_type_bus').id
        return [('provider_type_id.id', '=', int(domain_id))]

    def update_reference_code_internal(self):
        for idx, rec in enumerate(self.env['tt.reservation.visa.pricelist'].search([]), 1):
            if rec.provider_id == '':
                rec.reference_code = ''
                rec.provider_id = self.env['tt.provider'].search([('code', '=', 'visa_internal')], limit=1).id

    def get_reference_code(self):
        for idx, rec in enumerate(self.env['tt.reservation.visa.pricelist'].search([]),1):
            if rec.reference_code == '' or rec.reference_code == False:
                if rec.provider_id.code:
                    counter = idx
                    while True:
                        if not self.env['tt.reservation.visa.pricelist'].search([('reference_code', '=', rec.provider_id.code + rec.name + '_' + str(counter))]):
                            rec.update({
                                "reference_code": rec.provider_id.code + '_' + rec.name + '_' + str(counter),
                                "provider_id": self.env['tt.provider'].search([('code', '=', rec.provider_id.code)], limit=1).id
                            })
                            break
                        counter += 1
                else:
                    raise UserError(
                        _('You have to fill Provider ID in all Visa Pricelist.'))

            for count, requirement in enumerate(rec.requirement_ids):
                requirement.update({
                    "reference_code": '%s_%s' % (rec.reference_code, str(count))
                })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def actions_get_product_rodextrip(self, data):
        req = {
            'provider': 'rodextrip_visa'
        }
        res = self.env['tt.visa.api.con'].get_product_vendor(req)
        if res['error_code'] == 0:
            folder_path = '/var/log/tour_travel/rodextrip_visa_master_data'
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)
            file = open('/var/log/tour_travel/rodextrip_visa_master_data/rodextrip_visa_master_data.json', 'w')
            file.write(json.dumps(res['response']))
            file.close()
        else:
            #raise sini
            pass

    def actions_sync_product_rodextrip(self, data):
        provider = 'rodextrip_visa'
        list_product = self.env['tt.reservation.visa.pricelist'].search([('provider_id', '=', self.env['tt.provider'].search([('code', '=', 'rodextrip_visa')], limit=1).id)])
        for rec in list_product:
            rec.active = False
        file = []
        file_dat = open('/var/log/tour_travel/rodextrip_visa_master_data/rodextrip_visa_master_data.json','r')
        file = json.loads(file_dat.read())
        file_dat.close()
        if file:
            self.sync_products(provider, file)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def sync_product(self, provider=None, data=None, page=None):
        self.env['tt.master.bus.station'].action_bus_sync_data_traveloka()

    def sync_get_bus_journey(self, provider=None, data=None, page=None):
        self.env['tt.master.bus.station'].action_bus_sync_get_bus_journey_traveloka()

