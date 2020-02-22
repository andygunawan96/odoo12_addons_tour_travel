from odoo import api, fields, models, _


class HotelFacility(models.Model):
    _name = 'tt.hotel.facility'
    _description = 'Hotel Facility'

    name = fields.Char('Facility / Service Name', required=True)
    facility_type_id = fields.Many2one('tt.hotel.facility.type', 'Type of Facility / Service', required="True")
    description = fields.Char('Description')
    is_room_facility = fields.Boolean('Is Room Facility', default="False")
    is_hotel_facility = fields.Boolean('Is Hotel Facility', default="True")
    currency_id = fields.Many2one('res.currency', 'Currency')
    is_paid = fields.Boolean('Need Payment', default="False")
    css_class = fields.Char('Website CSS Class')
    internal_code = fields.Char('Internal Code')

    image_url = fields.Char('Image URL #1')
    image_url2 = fields.Char('Image URL #2')
    image_url3 = fields.Char('Image URL #3')


class HotelTopFacility(models.Model):
    _name = 'tt.hotel.top.facility'
    _description = 'Hotel Top Facility'
    _order = 'sequence, id'

    name = fields.Char('Name')
    facility_id = fields.Many2one('tt.hotel.facility', 'Facility')
    image_url = fields.Char('Image URL #1')
    image_url2 = fields.Char('Image URL #2')
    image_url3 = fields.Char('Image URL #3')
    sequence = fields.Integer('Sequence')
    internal_code = fields.Integer('Internal Code')
    active = fields.Boolean('Active', default=True)