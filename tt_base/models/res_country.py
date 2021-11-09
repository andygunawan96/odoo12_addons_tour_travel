from odoo import api, fields, models, _
from ...tools.api import Response
import logging, traceback

_logger = logging.getLogger(__name__)


class DestinationAlias(models.Model):
    _name = 'tt.destination.alias'
    _description = "Destination Alias Name"

    name = fields.Char('Name', required=True)
    city_id = fields.Many2one('res.city', 'City')
    state_id = fields.Many2one('res.country.state', 'State')
    country_id = fields.Many2one('res.country', 'Country')


class Country(models.Model):
    _inherit = 'res.country'
    _description = 'Tour & Travel - Res Country'

    phone_detail_ids = fields.One2many('phone.detail', 'country_id', string='Phone')
    city_ids = fields.One2many('res.city', 'country_id', string='Cities')
    other_name_ids = fields.One2many('tt.destination.alias', 'country_id', 'Dest. Alias',
                                     help='Destination Alias or Other Name')
    address_detail_ids = fields.One2many('address.detail', 'country_id', string='Addresses')
    provide_code_ids = fields.One2many('tt.provider.code', 'country_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    def get_country_data(self):
        res = {
            'name': self.name,
            'code': self.code,
            'phone_code': self.phone_code,
        }
        return res

    def get_country_data_by_code(self):
        _obj = self.sudo().search([('active', '=', True)])
        res = {}
        for rec in _obj:
            code = rec.code
            res.update({code: rec.get_country_data()})
        return res

    def get_country_list(self):
        _obj = self.sudo().search([('active', '=', True)])
        res = [rec.get_country_data() for rec in _obj]
        return res

    def get_country_list_api(self, data, context):
        try:
            response = self.get_country_list()
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Country Data API, %s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res

    def find_country_by_name(self, str_name, limit=1):
        if str_name:
            str_name = str_name.rstrip()
            found = self.search(['|', ('name', '=ilike', str_name), ('code', '=ilike', str_name)], limit=limit)
            if len(found) < limit:
                for rec in self.env['tt.destination.alias'].search([('name', 'ilike', str_name),('country_id','!=',False)], limit=limit-len(found)):
                    found += rec.country_id
            return found
        return False


class CountryState(models.Model):
    _inherit = "res.country.state"
    _description = 'Tour & Travel - Res Country State'

    city_ids = fields.One2many('res.city', 'state_id', string='Cities')
    provide_code_ids = fields.One2many('tt.provider.code', 'state_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    other_name_ids = fields.One2many('tt.destination.alias', 'state_id', 'Dest. Alias', help='Destination Alias or Other Name')
    address_detail_ids = fields.One2many('address.detail', 'state_id', string='Addresses')

    def find_state_by_name(self, str_name, limit=1):
        if str_name:
            str_name = str_name.rstrip()
            found = self.search([('name', '=ilike', str_name)], limit=limit)
            if len(found) < limit:
                for rec in self.env['tt.destination.alias'].search([('name', 'ilike', str_name),('state_id','!=',False)], limit=limit-len(found)):
                    found += rec.country_id
            return found
        return False


class CountryCity(models.Model):
    _inherit = 'res.city'
    _description = 'Tour & Travel - Res City'

    code = fields.Char('Internal Code', help="Code for internal channel")
    district_ids = fields.One2many('res.district', 'city_id', string='Districts')
    country_id = fields.Many2one('res.country', string='Country')
    provide_code_ids = fields.One2many('tt.provider.code', 'city_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    other_name_ids = fields.One2many('tt.destination.alias', 'city_id', 'Dest. Alias', help='Destination Alias or Other Name')
    address_detail_ids = fields.One2many('address.detail', 'city_id', string='Addresses')

    latitude = fields.Float('Latitude Degree', digits=(3, 7))
    longitude = fields.Float('Longitude Degree', digits=(3, 7))
    city_alias_name = fields.Char('Alias Name', compute='city_search_name', store=True)

    def find_city_by_name(self, str_name, limit=1, country_id=None):
        if str_name:
            str_name = str_name.rstrip()
            dom = []
            dom.append(('name', '=ilike', str_name))
            if country_id:
                dom.append(('country_id','=',country_id))
            found = self.search(dom, limit=limit)
            if len(found) < limit:
                for rec in self.env['tt.destination.alias'].search([('name', 'ilike', str_name), ('city_id','!=',False), ('city_id','not in', found.ids)], limit=limit-len(found)):
                    found += rec.city_id
            return found
        else:
            return False

    @api.onchange('name', 'other_name_ids')
    @api.depends('name', 'other_name_ids')
    def city_search_name(self):
        for rec1 in self:
            new_str = rec1.name
            if rec1.other_name_ids:
                new_str += ', '
                new_str += ', '.join([rec.name for rec in rec1.other_name_ids])
            rec1.city_alias_name = new_str


class CountryDistrict(models.Model):
    _name = 'res.district'
    _order = 'name'
    _description = 'Tour & Travel - Res District'

    name = fields.Char('Name', required=True)
    city_id = fields.Many2one('res.city', string='City')
    sub_district_ids = fields.One2many('res.sub.district', 'district_id', string='Sub Districts')
    active = fields.Boolean('Active', default=True)

    address_detail_ids = fields.One2many('address.detail', 'district_id', string='Addresses')


class CountrySubDistrict(models.Model):
    _name = 'res.sub.district'
    _order = 'name'
    _description = 'Tour & Travel - Res Sub District'

    name = fields.Char('Name', required=True)
    district_id = fields.Many2one('res.district', string='District')
    address_detail_ids = fields.One2many('address.detail', 'sub_district_id', string='Addresses')
    active = fields.Boolean('Active', default=True)
