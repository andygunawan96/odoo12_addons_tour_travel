from odoo import api, fields, models, _


class HotelImage(models.Model):
    _name = 'tt.hotel.image'
    _description = 'Hotel Image'
    _order = 'sequence'

    name = fields.Char('Name')
    sequence = fields.Integer(default=10)
    branch_url = fields.Char('Branch URL', help='Use this field for internal server image EX:')
    url = fields.Char('Full URL', required=True)
    provider_id = fields.Many2one('tt.provider', 'Provider')
    description = fields.Text('Description')

