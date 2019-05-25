from odoo import api,models,fields

class ServiceChargeAirline(models.Model):
    _inherit = "tt.service.charge"

    provider_airline_booking_id = fields.Many2one('tt.tb.provider.airline', 'Provider Booking ID')

    booking_airline_id = fields.Many2one('tt.reservation.airline', 'Booking', ondelete='cascade', index=True, copy=False)
