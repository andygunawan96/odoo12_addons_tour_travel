from odoo import api,models,fields
import pytz
import traceback
from ...tools.api import Response
import logging


_logger = logging.getLogger(__name__)


@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class Destinations(models.Model):
    _name = 'tt.destinations'
    _rec_name = 'display_name'
    _order = 'display_name'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    code = fields.Char('Code', help="Can be filled with IATA code", required=True)
    display_name = fields.Char('Display Name',store=True)
    country_id = fields.Many2one('res.country', 'Country')
    city = fields.Char('City', required=True, default='')
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

    @api.model
    def create(self, vals_list):
        vals_list.update({
            'display_name': '%s - %s ( %s )' % (vals_list.get('city', ''), vals_list['name'], vals_list['code'])
        })
        return super(Destinations, self).create(vals_list)

    def write(self, vals):
        for rec in self:
            vals.update({
                'display_name': '%s - %s ( %s )' % (vals.get('city', rec.city), vals.get('name',rec.name),vals.get('code', rec.code))
            })
            super(Destinations, self).write(vals)


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
            'country_id': {
                'name': self.country_id.name and self.country_id.name or '',
                'code': self.country_id.code and self.country_id.code or '',
                'phone_code': self.country_id.phone_code and self.country_id.phone_code or '',
            },
            'city': self.city and self.city or '',
            'timezone_hour': self.timezone_hour and self.timezone_hour or 0,
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
            data.pop('country_id')
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

    def get_destination_list_api(self, data, context):
        try:
            filter_by = data.get('filter_by', '')
            if filter_by == 'code':
                response = self.get_destination_list_by_code(data['provider_type'])
            else:
                response = self.get_destination_list_by_country_code(data['provider_type'])
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Destination List API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res
