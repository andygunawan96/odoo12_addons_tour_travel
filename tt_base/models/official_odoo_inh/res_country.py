from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ....tools.api import Response
import logging, traceback

_logger = logging.getLogger(__name__)


class DestinationAlias(models.Model):
    _name = 'tt.destination.alias'
    _description = "Destination Alias Name"

    name = fields.Char('Name', required=True)
    city_id = fields.Many2one('res.city', 'City')
    state_id = fields.Many2one('res.country.state', 'State')
    country_id = fields.Many2one('res.country', 'Country')

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 370')
        return super(DestinationAlias, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 371')
        return super(DestinationAlias, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 372')
        return super(DestinationAlias, self).unlink()


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

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(Country, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(Country, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(Country, self).unlink()

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
        _obj = self.sudo().search([('active', '=', True), ('code', '!=', False)])
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
            search_params = [('name','=ilike',str_name)]
            if len(str_name) == 2:
                search_params = ['|',search_params[0],('code','=ilike',str_name)]
            found = self.search(search_params, limit=limit)
            if len(found) < limit:
                for rec in self.env['tt.destination.alias'].search([('name', '=ilike', str_name),('country_id','!=',False)], limit=limit-len(found)):
                    found += rec.country_id
            return found
        return False

    # November 11, 2021 - SAM
    # New Get Country API
    def get_country_api(self):
        try:
            objs = self.env['res.country'].sudo().search([])
            country_data = {
                'country_dict': {}
            }
            for obj in objs:
                if not obj.active:
                    continue

                vals = obj.get_country_data()
                country_code = vals['code']
                if not country_code:
                    continue

                country_data['country_dict'][country_code] = vals

            payload = {
                'country_data': country_data
            }
        except Exception as e:
            _logger.error('Error Get Country Data, %s' % traceback.format_exc())
            payload = {}
        return payload


class CountryState(models.Model):
    _inherit = "res.country.state"
    _description = 'Tour & Travel - Res Country State'

    city_ids = fields.One2many('res.city', 'state_id', string='Cities')
    provider_code_ids = fields.One2many('tt.provider.code', 'state_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    other_name_ids = fields.One2many('tt.destination.alias', 'state_id', 'Dest. Alias', help='Destination Alias or Other Name')
    address_detail_ids = fields.One2many('address.detail', 'state_id', string='Addresses')

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountryState, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountryState, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountryState, self).unlink()

    def find_state_by_name(self, str_name, limit=1, country_id=None):
        if str_name:
            str_name = str_name.rstrip()
            dom = ['|', ('name', '=ilike', str_name), ('code', '=ilike', str_name)]
            if country_id:
                dom.append(('country_id', '=', country_id))
            found = self.search(dom, limit=limit)
            if len(found) < limit:
                for rec in self.env['tt.destination.alias'].search([('name', '=ilike', str_name),('state_id','!=',False)], limit=limit-len(found)):
                    found += rec.state_id
            return found
        return False


class CountryCity(models.Model):
    _inherit = 'res.city'
    _description = 'Tour & Travel - Res City'

    code = fields.Char('Internal Code', help="Code for internal channel")
    district_ids = fields.One2many('res.district', 'city_id', string='Districts')
    country_id = fields.Many2one('res.country', string='Country')
    provider_code_ids = fields.One2many('tt.provider.code', 'city_id', string='Provide Code')
    active = fields.Boolean('Active', default=True)

    other_name_ids = fields.One2many('tt.destination.alias', 'city_id', 'Dest. Alias', help='Destination Alias or Other Name')
    address_detail_ids = fields.One2many('address.detail', 'city_id', string='Addresses')

    latitude = fields.Float('Latitude Degree', digits=(3, 7))
    longitude = fields.Float('Longitude Degree', digits=(3, 7))
    city_alias_name = fields.Char('Alias Name', compute='city_search_name', store=True)

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountryCity, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountryCity, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountryCity, self).unlink()

    def find_city_by_name(self, str_name, limit=1, country_id=None, state_id=None):
        if str_name:
            str_name = str_name.rstrip()
            dom = []
            dom.append(('name', '=ilike', str_name))
            if country_id:
                dom.append(('country_id','=',country_id))
            if state_id:
                dom.append(('state_id','=',state_id))
            found = self.search(dom, limit=limit)
            if len(found) < limit:
                for rec in self.env['tt.destination.alias'].search([('name', '=ilike', str_name), ('city_id','!=',False), ('city_id','not in', found.ids)], limit=limit-len(found)):
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

    def get_full_name(self):
        for rec in self:
            full_name = rec.name
            if rec.state_id:
                full_name += '; ' + rec.state_id.name
                if rec.state_id.country_id:
                    full_name += '; ' + rec.state_id.country_id.name
            elif rec.country_id:
                full_name += '; ' + rec.country_id.name
            return full_name


class CountryDistrict(models.Model):
    _name = 'res.district'
    _order = 'name'
    _description = 'Tour & Travel - Res District'

    name = fields.Char('Name', required=True)
    city_id = fields.Many2one('res.city', string='City')
    sub_district_ids = fields.One2many('res.sub.district', 'district_id', string='Sub Districts')
    active = fields.Boolean('Active', default=True)

    address_detail_ids = fields.One2many('address.detail', 'district_id', string='Addresses')

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountryDistrict, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountryDistrict, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountryDistrict, self).unlink()


class CountrySubDistrict(models.Model):
    _name = 'res.sub.district'
    _order = 'name'
    _description = 'Tour & Travel - Res Sub District'

    name = fields.Char('Name', required=True)
    district_id = fields.Many2one('res.district', string='District')
    address_detail_ids = fields.One2many('address.detail', 'sub_district_id', string='Addresses')
    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountrySubDistrict, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountrySubDistrict, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 373')
        return super(CountrySubDistrict, self).unlink()
