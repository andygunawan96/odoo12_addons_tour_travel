from odoo import models, fields


class ServiceChargeTour(models.Model):
    _inherit = "tt.service.charge"

    tour_id = fields.Many2one('tt.reservation.tour', 'Booking', ondelete='cascade', index=True, copy=False)