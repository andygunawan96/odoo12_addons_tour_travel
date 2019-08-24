from odoo import api, fields, models, _
from ...tools import test_to_dict
from ...tools.api import Response
import logging, traceback


_logger = logging.getLogger(__name__)


class Country(models.Model, test_to_dict.ToDict):
    _inherit = 'res.country'
    _description = 'Tour & Travel - Res Country'

    phone_detail_ids = fields.One2many('phone.detail', 'country_id', string='Phone')
    city_ids = fields.One2many('res.city', 'country_id', string='Cities')
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


class CountryState(models.Model,test_to_dict.ToDict):
    _inherit = "res.country.state"
    _description = 'Tour & Travel - Res Country State'

    city_ids = fields.One2many('res.city', 'state_id', string='Cities')
    provide_code_ids = fields.One2many('tt.provider.code', 'state_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    address_detail_ids = fields.One2many('address.detail', 'state_id', string='Addresses')


class CountryCity(models.Model,test_to_dict.ToDict):
    _inherit = 'res.city'
    _description = 'Tour & Travel - Res City'

    code = fields.Char('Skytors Code', help="Code for skytors' channel")
    district_ids = fields.One2many('res.district', 'city_id', string='Districts')
    country_id = fields.Many2one('res.country', string='Country')
    provide_code_ids = fields.One2many('tt.provider.code', 'city_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    address_detail_ids = fields.One2many('address.detail', 'city_id', string='Addresses')


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
