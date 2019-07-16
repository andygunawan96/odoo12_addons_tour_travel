from odoo import api, fields, models, _


class CustomerDetails(models.Model):
    _inherit = 'tt.customer'

    domicile = fields.Char('Domicile')
    visa_id = fields.Many2one('tt.reservation.visa', 'Visa ID')
