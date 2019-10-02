from odoo import models, fields


class ServiceChargeTour(models.Model):
    _inherit = "tt.service.charge"

    provider_tour_booking_id = fields.Many2one('tt.provider.tour', 'Provider Booking ID')

    booking_tour_id = fields.Many2one('tt.reservation.tour', 'Booking', ondelete='cascade', index=True,
                                          copy=False)

    passenger_tour_ids = fields.Many2many('tt.reservation.passenger.tour',
                                              'tt_reservation_tour_cost_charge_rel', 'service_charge_id',
                                              'passenger_id', 'Passenger Tour')
