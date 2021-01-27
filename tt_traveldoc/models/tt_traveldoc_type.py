from odoo import api, fields, models, _


class TraveldocType(models.Model):
    _name = 'tt.traveldoc.type'
    _description = 'Travel Document Type'

    name = fields.Char('Document Name')
    description = fields.Char('Description')
