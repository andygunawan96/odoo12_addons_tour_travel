from odoo import api,models,fields
from odoo.exceptions import UserError
import pytz
import traceback
from ...tools.api import Response
import logging
import copy
from datetime import datetime, timedelta
from ...tools import util, ERR


_logger = logging.getLogger(__name__)
FORMAT_DATETIME = '%Y-%m-%d %H:%M:%S'
EXPIRED_SECONDS = 300


@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class Destinations(models.Model):
    _name = 'tt.destinations'
    _inherit = 'tt.history'
    _rec_name = 'display_name'
    _order = 'display_name'
    _description = 'Destinations'

    name = fields.Char('Name', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    code = fields.Char('Code', help="Can be filled with IATA code", required=True)
    display_name = fields.Char('Display Name',compute="_compute_display_name_rodex",store=True)
    country_id = fields.Many2one('res.country', 'Country')
    city = fields.Char('City', required=True, default='')
    city_id = fields.Many2one('res.city', 'City ID')
    icao = fields.Char('ICAO', help="for airline : 4-letter ICAO code")
    latitude = fields.Float('Latitude Degree', digits=(3,7))
    longitude = fields.Float('Longitude Degree', digits=(3,7))
    altitude = fields.Float('Altitude', digits=(3,7))
    timezone_hour = fields.Float('Timezone Hour')
    daylight_saving_times = fields.Char('Daylight Saving Times')
    tz = fields.Selection(_tz_get, string='Timezone', default=lambda self: self._context.get('tz'))
    # source = fields.Char('Source')
    # is_international_flight = fields.Boolean('International Flight', default=True)
    active = fields.Boolean('Active', default=True)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('tt_base.group_destination_level_5'):
            raise UserError('Action failed due to security restriction. Required Destination Level 5 permission.')
        return super(Destinations, self).unlink()

    @api.multi
    @api.depends('city','name','code')
    def _compute_display_name_rodex(self):
        for rec in self:
            rec.display_name = '%s - %s (%s)' % (rec.city or '', rec.name or '', rec.code or '')


    def get_id(self, code, provider_type):
        res = self.sudo().search([('code','=',code),('provider_type_id', '=', provider_type.id)])
        return res and res[0].id or False

    def to_dict(self):
        return {
            'name': self.name,
            'provider_type_id': self.provider_type_id.to_dict(),
            'code': self.code,
            'country': {
                'name': self.country_id.name,
                'code': self.country_id.code,
                'phone_code': self.country_id.phone_code
            },
            'city': self.city,
            'icao': self.icao,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'timezone_hour': self.timezone_hour,
            'daylight_saving_times': self.daylight_saving_times,
            'tz': self.tz,
            'active': self.active
        }

    def get_destination_data(self):
        res = {
            'name': self.name,
            'code': self.code,
            'city': self.city and self.city or '',
            'timezone_hour': self.timezone_hour and self.timezone_hour or 0,
            'active': self.active,
        }
        return res

    def get_destination_list_by_country_code(self, _provider_type):
        provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
        if not provider_obj:
            raise Exception('Provider type not found, %s' % _provider_type)

        _obj = self.sudo().search([('provider_type_id', '=', provider_obj.id), ('active', '=', True)])
        res = {}
        for rec in _obj:
            if not rec.country_id:
                continue
            country_code = rec.country_id.code
            if not res.get(country_code):
                res[country_code] = []
            data = rec.get_destination_data()
            # data.pop('country_id')
            res[country_code].append(data)
        return res

    def get_destination_list_by_code(self, _provider_type):
        provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
        if not provider_obj:
            raise Exception('Provider type not found, %s' % _provider_type)

        _obj = self.sudo().search([('provider_type_id', '=', provider_obj.id), ('active', '=', True)])
        res = {}
        for rec in _obj:
            code = rec.code
            res.update({code: rec.get_destination_data()})
        return res

    def get_destination_list_by_country(self, _provider_type, is_all_data=False):
        provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
        if not provider_obj:
            raise Exception('Provider type not found, %s' % _provider_type)

        param = [('provider_type_id', '=', provider_obj.id)]
        if not is_all_data:
            param.append(('active', '=', True))
        # _obj = self.sudo().search(param)
        _obj = self.sudo().with_context(active_test=False).search(param)
        country_dict = {}
        for rec in _obj:
            country_code = rec.country_id.code
            if not country_code:
                continue
            country_obj = country_dict.get(country_code)
            if not country_obj:
                country_dict[country_code] = rec.country_id.get_country_data()
                country_obj = country_dict[country_code]
                country_obj['destinations'] = []
            country_obj['destinations'].append(rec.get_destination_data())

        res = [vals for vals in country_dict.values()]
        return res

    def get_destination_list_api(self, data, context):
        try:
            # August 23, 2019 - SAM
            # Update response untuk get destination list
            # filter_by = data.get('filter_by', '')
            # if filter_by == 'code':
            #     response = self.get_destination_list_by_code(data['provider_type'])
            # else:
            #     response = self.get_destination_list_by_country_code(data['provider_type'])
            is_all_data = data.get('is_all_data', False)
            response = self.get_destination_list_by_country(data['provider_type'], is_all_data)
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Destination List API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def get_city(self):
        for rec in self.search([]):
            # _logger.info('Finding: ' + rec.city)
            for rec2 in self.env['res.city'].find_city_by_name(rec.city, limit=5):
                if rec.country_id == rec2.country_id:
                    # _logger.info('Found: ' + rec2.name + '(' + rec2.country_id.name + ')')
                    rec.city_id = rec2
                    break
        return True

    def remove_city(self):
        for rec in self.search([]):
            rec.city_id = False

    def get_all_city_for_insurance(self):
        res = {}
        data = self.search([])
        for rec in data:
            if not res.get(rec.country_id.name):
                res[rec.country_id.name] = []
            if not rec.city in res[rec.country_id.name]:
                res[rec.country_id.name].append(rec.city)
        return ERR.get_no_error(res)

    # November 10, 2021 - SAM
    # New Get Data API Function for DestinationToolsV3
    def get_destination_data_api(self):
        try:
            objs = self.env['tt.destinations'].sudo().search([])
            destination_data = {}
            date_now = datetime.now().strftime(FORMAT_DATETIME)
            expired_date = datetime.now() + timedelta(seconds=EXPIRED_SECONDS)
            expired_date = expired_date.strftime(FORMAT_DATETIME)

            country_data = {}
            for obj in objs:
                if not obj.active:
                    continue

                provider_type = obj.provider_type_id.code if obj.provider_type_id else ''
                if not provider_type:
                    continue

                vals = obj.get_destination_data()
                destination_code = vals['code']

                if not destination_code:
                    continue

                country_code = obj.country_id.code if obj.country_id else ''
                if country_code and country_code not in country_data:
                    country_data[country_code] = obj.country_id.get_country_data()

                vals.update({
                    'country_code': country_code,
                    'country_id': country_data.get(country_code, {})
                })

                if provider_type not in destination_data:
                    destination_data[provider_type] = {
                        # 'destination_list': [],
                        'destination_dict': {},
                        'create_date': date_now,
                        'expired_date': expired_date,
                    }
                # destination_data[provider_type]['destination_list'].append(vals)
                destination_data[provider_type]['destination_dict'][destination_code] = vals

            payload = {
                'destination_data': destination_data
            }
        except Exception as e:
            _logger.error('Error Get Destination Data, %s' % traceback.format_exc())
            payload = {}
        return payload
    # END
