# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import requests, zipfile, json, os

import logging
_logger = logging.getLogger(__name__)


class HotelImageSettings(models.Model):
    _name = 'hotel.image.settings'
    _description = 'Hotel Image Settings'

    default_url = fields.Char('Default url', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).default_url)
    empty_image = fields.Char('Default Empty Image', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).empty_image)
    default_banner_ids = fields.Many2many('tt.image.banner', 'default_banner_rel', 'image_setting_id', 'banner_id'
                                          , 'Banner(s)', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).default_banner_ids.ids)
    home_limit = fields.Integer('Home Banner Limit', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).home_limit)
    city_limit = fields.Integer('City Page Limit', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).city_limit)

    show_provider = fields.Boolean('Show Provider', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).show_provider)
    show_multi_price = fields.Boolean('Show Multi Price', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).show_multi_price)
    direct_search = fields.Boolean('Direct Search', help='Direct Search to Available Vendor; If not activated then search from cache first',
                                   default=lambda self: self.env['hotel.image.settings'].search([],limit=1).direct_search)

    allowed_agent_ids = fields.Many2many('res.partner', 'allowed_agent_rel', 'image_setting_id', 'agent_id', 'Allowed Agent', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).allowed_agent_ids.ids)

    # File Reader
    file_url = fields.Char('File URL', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).file_url)
    file_name = fields.Selection([('hotels-', 'Hotel'), ('countries-', 'Country'), ('facilities-', 'Facility'),
                                  ('hoteltypes-', 'Hotel Type'), ('destinations-', 'Destination')], 'Name', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).file_name)
    number = fields.Integer('File Number', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).number)
    extension = fields.Char('Extension', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).extension)
    provider_id = fields.Many2one('res.partner', 'Provider', domain="[('is_vendor','=','vendor'),('parent_id','=',False)]",
                                  default=lambda self: self.env['hotel.image.settings'].search([], limit=1).provider_id.id)

    remove_str = fields.Text('Remove string in similar search', help="Penulisan 1 kata kunci dipisahkan dengan ';' tanpa spasi (' ')\n"
                                                                         "Example: hotel;villa;apartment", default=lambda self: self.env['hotel.image.settings'].search([], limit=1).remove_str)

    hotel_cache = fields.Text('Hotel Cache', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).hotel_cache)
    hotel_number = fields.Integer('Number(s)', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).hotel_number)
    hotel_state = fields.Selection([('ongoing','On Going'), ('done','Done')], 'State', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).hotel_state)
    city_cache = fields.Text('City Cache', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).city_cache)
    city_number = fields.Integer('Number(s)', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).city_number)
    city_state = fields.Selection([('ongoing', 'On Going'), ('done', 'Done')], 'State', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).city_state)
    country_cache = fields.Text('Country Cache', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).country_cache)
    country_number = fields.Integer('Number(s)', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).country_number)
    country_state = fields.Selection([('ongoing', 'On Going'), ('done', 'Done')], 'State', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).country_state)
    landmark_cache = fields.Text('Landmark Cache', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).landmark_cache)
    landmark_number = fields.Integer('Number(s)', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).landmark_number)
    landmark_state = fields.Selection([('ongoing', 'On Going'), ('done', 'Done')], 'State', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).landmark_state)

    scrap_provider_id = fields.Many2one('res.partner', 'Provider', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).scrap_provider_id.id)
    city_ids = fields.Many2many('res.city', 'scarp_city_rel', 'image_setting_id', 'city_id', 'City', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).city_ids.ids)
    scrap_limit = fields.Integer('Limit', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).scrap_limit, help='Limit hotel response for this Scrap')
    scrap_history_ids = fields.Many2many('scrap.history', 'scrap_history_rel', 'image_setting_id', 'scrap_id', 'History', default=lambda self: self.env['hotel.image.settings'].search([], limit=1).scrap_history_ids.ids)

    @api.one
    def execute(self):
        obj = self.env['hotel.image.settings'].search([], limit=1)
        obj.sudo().write({
            'default_url': self.default_url,
            'empty_image': self.empty_image,
            'default_banner_ids': [(6, 0, self.default_banner_ids.ids)],
            'home_limit': self.home_limit,
            'city_limit': self.city_limit,
            'show_provider': self.show_provider,
            'show_multi_price': self.show_multi_price,
            'direct_search': self.direct_search,
            'allowed_agent_ids': [(6, 0, self.allowed_agent_ids.ids)],
            # 'compare_fields_ids': self.compare_fields_ids.ids,
            'file_url': self.file_url,
            'file_name': self.file_name,
            'number': self.number,
            'extension': self.extension,
            'provider_id': self.provider_id.id,
            'remove_str': self.remove_str,
            'hotel_cache': self.hotel_cache,
            'hotel_number': self.hotel_number,
            'hotel_state': self.hotel_state,
            'city_cache': self.city_cache,
            'city_number': self.city_number,
            'city_state': self.city_state,
            'country_cache': self.country_cache,
            'country_number': self.country_number,
            'country_state': self.country_state,
            'landmark_cache': self.landmark_cache,
            'landmark_number': self.landmark_number,
            'landmark_state': self.landmark_state,
            'scrap_provider_id': self.scrap_provider_id.id,
            'city_ids': [(6, 0, self.city_ids.ids)],
            'scrap_limit': self.scrap_limit,
            'scrap_history_ids': [(6, 0, self.scrap_history_ids.ids)],
        })

    @api.one
    def get_record(self):
        history_id = self.env['hotel.content.history'].create({
            'file_name': self.file_name,
            'provider_id': self.provider_id.id,
            'start': self.number,
        })
        state, number = self.env['tt.hotel'].get_record_by_file(self.file_url, self.file_name, self.number, self.extension, self.provider_id.id)
        obj = self.env['hotel.image.settings'].search([], limit=1)
        obj.sudo().write({'number': state != 'done' and number or 1,})
        history_id.update({'end': number, 'state': state})
        self._cr.commit()
        raise UserError('Get Record : ' + state != 'done' and 'Stop in ' + str(number) or 'Done')

    @api.one
    def get_record_by_url(self):
        # Load Rec from URL
        # r = requests.get('https://assets.cosmos-data.com/exports/consumer-20190114-export.tar.bz2', allow_redirects=True)
        # Save downloaded data to local location
        # open('/home/rodex-it-05/Documents/VIN/Document/Hotel/Api./HotelPro/01_DEV/Data/consumer-20190114-export.tar.bz2', 'wb').write(r.content)
        # Unzip File
        with zipfile.ZipFile('/home/rodex-it-05/Documents/VIN/Document/Hotel/Api./HotelPro/01_DEV/Data/consumer-20190114-export.tar.bz2', "r") as zip_ref:
            zip_ref.extractall("targetdir")
        return True

    @api.multi
    def prepare_gateway_cache(self):
        return {
            'hotel_ids': json.loads(self.hotel_cache),
            'city_ids': json.loads(self.city_cache),
            'country_ids': json.loads(self.country_cache),
            'landmark_ids': json.loads(self.landmark_cache)
        }

    def remove_cache_hotel(self):
        self.hotel_state = 'ongoing'
        self.hotel_cache = ''
        self.hotel_number = 0
        self.execute()

    def render_cache_hotel(self):
        self.hotel_state = 'ongoing'
        hotel_str = json.loads(self.hotel_cache and self.hotel_cache or json.dumps([]))
        hotel_count = self.env['tt.hotel'].sudo().search_count([])
        while self.hotel_number < hotel_count:
            hotel_str += self.env['test.search'].sudo().get_provider_hotel_detail(self.env['tt.hotel'].sudo().search([], limit=50, offset=self.hotel_number).ids, '')
            # Buat File jika total data lebih dari 1k
            # Lalu hapus data di hotel_cache
            self.hotel_number += 50
            _logger.info('Render Hotel Cache until number ' + str(self.hotel_number))
            if self.hotel_number >= 1000 and self.hotel_number % 1000 == 0:
                self.hotel_cache = False
                filename = "cache_hotel_" + str(self.hotel_number / 1000) + ".txt"
                _logger.info('Write in directory ' + os.path.abspath(filename))

                file = open(filename, 'w')
                file.write(json.dumps(hotel_str))
                file.close()
                hotel_str = []
            else:
                self.hotel_cache = json.dumps(hotel_str)
            self.execute()
            self._cr.commit()
        self.hotel_state = 'done'
        _logger.info('Render Hotel Cache done')
        return self.execute()

    def render_cache_city(self):
        self.city_number = 0
        self.city_state = 'ongoing'
        str = json.loads(self.city_cache and self.city_cache or json.dumps([]))
        str += [self.env['test.search'].sudo().get_provider_city_detail(rec) for rec in self.env['res.city'].sudo().search([])]
        self.city_cache = json.dumps(str)
        self.city_number = len(str)
        self.city_state = 'done'
        return self.execute()

    def render_cache_country(self):
        self.country_number = 0
        self.country_state = 'ongoing'
        str = json.loads(self.country_cache and self.country_cache or json.dumps([]))
        str += self.env['test.search'].sudo().prepare_countries(self.env['res.country'].sudo().search([]))
        self.country_cache = json.dumps(str)
        self.country_number = len(str)
        self.country_state = 'done'
        return self.execute()

    def render_cache_landmark(self):
        self.landmark_number = 0
        self.landmark_state = 'ongoing'
        str = json.loads(self.landmark_cache and self.landmark_cache or json.dumps([]))
        str += self.env['test.search'].sudo().prepare_landmark(self.env['tt.landmark'].sudo().search([]))
        self.landmark_cache = json.dumps(str)
        self.landmark_number = len(str)
        self.landmark_state = 'done'
        return self.execute()

    def scrap_hotel_to_gw(self):
        a = []
        for city_id in self.city_ids.ids:
            scrap_history_id = self.env['scrap.history'].sudo().create({
                'provider_id': self.scrap_provider_id.id,
                'city_id': city_id,
                'limit': self.scrap_limit,
                'state': 'ongoing'
            })
            a.append(scrap_history_id.id)
            try:
                scrap_history_id.sudo().request_scrap()
            except:
                scrap_history_id.sudo().update({'state': 'error'})
                # pass
            self.scrap_history_ids = [(6, 0, a)]
            return self.execute()


# class HotelCompareFields(models.Model):
#     _name = 'hotel.compare.field'
#
#     compare_id = fields.Many2one('hotel.image.settings', 'Compare')
#     name = fields.Char('Name')
#     field_name = fields.Char('Field')
#     used = fields.Boolean('Active')
#
#
# class HotelInformationCompare(models.Model):
#     _inherit = 'tt.hotel.compare'
#
#     def get_compared_param(self):
#         return [obj.field_name for obj in self.env['hotel.compare.field'].search([('used', '=', True)]) ]


class HotelContentHistory(models.Model):
    _name = 'hotel.content.history'
    _description = 'Hotel Content History'

    file_name = fields.Selection([('hotels-', 'Hotel'), ('countries-', 'Country'), ('facilities-', 'Facility'),
                                  ('hoteltypes-', 'Hotel Type'), ('destinations-', 'Destination')], 'Name')
    provider_id = fields.Many2one('res.partner', 'Provider')
    start = fields.Integer('Start')
    end = fields.Integer('End')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('error', 'Error')], 'State', default='draft')
