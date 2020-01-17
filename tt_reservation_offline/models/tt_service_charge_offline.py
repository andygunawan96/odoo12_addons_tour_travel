from odoo import api, models, fields


class ServiceChargeOffline(models.Model):
    _inherit = "tt.service.charge"

    provider_offline_booking_id = fields.Many2one('tt.provider.offline', 'Provider Booking ID')

    booking_offline_id = fields.Many2one('tt.reservation.offline', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_offline_ids = fields.Many2many('tt.reservation.offline.passenger',
                                             'tt_reservation_offline_cost_charge_rel', 'service_charge_id', 'passenger_id',
                                             'Passenger Offline', readonly=False)
