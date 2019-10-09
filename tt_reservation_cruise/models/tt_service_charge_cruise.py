from odoo import api, models, fields


class ServiceChargeCruise(models.Model):
    _inherit = "tt.service.charge"

    booking_cruise_id = fields.Many2one('tt.reservation.cruise', 'Booking', ondelete='cascade', index=True, copy=False)