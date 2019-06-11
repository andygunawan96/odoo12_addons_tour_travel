from odoo import api, fields, models, _


class CustomerDetails(models.Model):
    _inherit = 'tt.customer'

    domicile = fields.Char('Domicile')
