from odoo import api, fields, models, _


class HotelType(models.Model):
    _name = 'tt.hotel.type'
    _description = 'Hotel Type (hotel, motel, villa, apartment)'

    name = fields.Char('Hotel type', required="True")
    usage = fields.Selection([('hotel', 'Hotel'), ('theme', 'ThemePark')], string='Usage')
    description = fields.Text('Description')
