from odoo import api,models,fields


class TtServiceChargeAirline(models.Model):
    _inherit = "tt.service.charge"

    provider_activity_booking_id = fields.Many2one('tt.provider.activity', 'Provider Booking ID')

    booking_activity_id = fields.Many2one('tt.reservation.activity', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_activity_ids = fields.Many2many('tt.reservation.passenger.activity', 'tt_reservation_activity_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Activity')