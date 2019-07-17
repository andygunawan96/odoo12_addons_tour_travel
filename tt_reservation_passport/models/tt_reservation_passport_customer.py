from odoo import api, fields, models, _


class CustomerDetails(models.Model):
    _inherit = 'tt.customer'

    domicile = fields.Char('Domicile')
    passport_id = fields.Many2one('tt.reservation.passport', 'Passport ID')
