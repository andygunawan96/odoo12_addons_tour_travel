from odoo import api, fields, models, _


class TraveldocType(models.Model):
    _name = 'tt.traveldoc.type'

    name = fields.Char('Document Name')
    description = fields.Char('Description')
