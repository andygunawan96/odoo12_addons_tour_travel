from odoo import api, models, fields


class ServiceChargeOffline(models.Model):
    _inherit = "tt.service.charge"

    provider_offline_booking_id = fields.Many2one('tt.tb.provider.offline', 'Provider Booking ID')

    booking_offline_id = fields.Many2one('tt.reservation.offline', 'Booking', ondelete='cascade', index=True, copy=False)
