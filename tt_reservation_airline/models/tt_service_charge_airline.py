from odoo import api,models,fields

class TtServiceChargeAirline(models.Model):
    _inherit = "tt.service.charge"

    provider_airline_booking_id = fields.Many2one('tt.provider.airline', 'Provider Booking ID')

    booking_airline_id = fields.Many2one('tt.reservation.airline', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_airline_id = fields.Many2one('tt.reservation.passenger.airline', 'Passenger Airline')