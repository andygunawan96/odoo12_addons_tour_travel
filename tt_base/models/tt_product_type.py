from odoo import api, fields, models, _


class TtProductType(models.Model):
    _name = 'tt.product.type'

    name = fields.Char('Name')
    ref_number = fields.Integer('Reference Number')
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)
