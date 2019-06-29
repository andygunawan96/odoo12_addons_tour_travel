from odoo import models, fields


class ResBank(models.Model):
    _inherit = ['tt.history']
    _name = 'models'
    _rec_name = 'name'
    _description = 'Tour & Travel - Models'

    name = fields.Char('Name')