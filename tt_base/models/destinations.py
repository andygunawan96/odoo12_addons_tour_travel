from odoo import api,models,fields
import pytz

@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class Destinations(models.Model):
    _name = 'tt.destinations'
    _rec_name = 'display_name'
    _order = 'display_name'

    name = fields.Char('Name', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    code = fields.Char('Code', help="Can be filled with IATA code")
    display_name = fields.Char('Display Name',store=True)
    country_id = fields.Many2one('res.country', 'Country', required=False)
    city = fields.Char('City')
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
            'display_name': '%s - %s ( %s )' % (vals_list['city'], vals_list['name'], vals_list['code'])
        })
        return super(Destinations, self).create(vals_list)

    def write(self, vals):
        vals.update({
            'display_name': '%s - %s ( %s )' % (vals.get('city',self.city), vals.get('name',self.name),vals.get('code',self.code))
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
