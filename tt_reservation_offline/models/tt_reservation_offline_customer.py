from odoo import api, fields, models, _


class CustomerDetails(models.Model):
    _inherit = 'tt.customer'

    reservation_offline_id = fields.Many2one('tt.reservation.offline', 'Issued Offline ID')
