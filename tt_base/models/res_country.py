from odoo import api, fields, models, _
from ...tools import test_to_dict

class Country(models.Model,test_to_dict.ToDict):
    _inherit = 'res.country'
    _description = 'Tour & Travel - Res Country'

    city_ids = fields.One2many('res.city', 'country_id', string='Cities')
    # provide_code_ids = fields.One2many('tt.provider.code', 'group_booking_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    # address_detail_ids = fields.One2many('address.detail', 'country_id', string='Addresses')
    # phone_detail_ids = fields.One2many('phone.detail', 'country_id', string='Phone')


class CountryState(models.Model,test_to_dict.ToDict):
    _inherit = "res.country.state"
    _description = 'Tour & Travel - Res Country State'

    city_ids = fields.One2many('res.city', 'state_id', string='Cities')
    # provide_code_ids = fields.One2many('tt.provider.code', 'group_booking_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    # address_detail_ids = fields.One2many('address.detail', 'state_id', string='Addresses')


class CountryCity(models.Model,test_to_dict.ToDict):
    _inherit = 'res.city'
    _description = 'Tour & Travel - Res City'

    code = fields.Char('Skytors Code', help="Code for skytors' channel")
    district_ids = fields.One2many('res.district', 'city_id', string='Districts')
    country_id = fields.Many2one('res.country', string='Country')
    # provide_code_ids = fields.One2many('tt.provider.code', 'group_booking_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    # address_detail_ids = fields.One2many('address.detail', 'city_id', string='Addresses')


class CountryDistrict(models.Model):
    _name = 'res.district'
    _order = 'name'
    _description = 'Tour & Travel - Res District'

    name = fields.Char('Name', required=True)
    city_id = fields.Many2one('res.city', string='City')
    sub_district_ids = fields.One2many('res.sub.district', 'district_id', string='Sub Districts')
    active = fields.Boolean('Active', default=True)

    # address_detail_ids = fields.One2many('address.detail', 'district_id', string='Addresses')


class CountrySubDistrict(models.Model):
    _name = 'res.sub.district'
    _order = 'name'
    _description = 'Tour & Travel - Res Sub District'

    name = fields.Char('Name', required=True)
    district_id = fields.Many2one('res.district', string='District')
    active = fields.Boolean('Active', default=True)

    # address_detail_ids = fields.One2many('address.detail', 'sub_district_id', string='Addresses')
