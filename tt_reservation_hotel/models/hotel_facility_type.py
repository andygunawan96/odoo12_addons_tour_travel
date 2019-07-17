from odoo import api, fields, models, _


class HotelFacilityGroup(models.Model):
    _name = 'tt.hotel.facility.group'
    _description = 'Facility Grouping'

    name = fields.Char('Name', required="True")
    type_ids = fields.One2many('tt.hotel.facility.type', 'group_id', 'Facility')
    description = fields.Text('Description')


class HotelFacilityType(models.Model):
    _name = 'tt.hotel.facility.type'
    _description = 'Facility Type'

    name = fields.Char('Name', required="True")
    description = fields.Text('Description')
    group_id = fields.Many2one('tt.hotel.facility.group', 'Group')
    is_price = fields.Boolean('Price', default=False)


