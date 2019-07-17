from odoo import api, fields, models, _


class RoomType(models.Model):
    _name = 'tt.room.type'
    _description = 'Room Type (Superrior, Double, Twin, Loft etc)'

    name = fields.Char('Name')
    guest_count = fields.Integer('Person Capacity')