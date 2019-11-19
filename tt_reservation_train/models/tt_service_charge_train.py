from odoo import api,models,fields

class TtServiceChargeTrain(models.Model):
    _inherit = "tt.service.charge"

    provider_train_booking_id = fields.Many2one('tt.provider.train', 'Provider Booking ID')

    booking_train_id = fields.Many2one('tt.reservation.train', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_train_ids = fields.Many2many('tt.reservation.passenger.train', 'tt_reservation_train_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Train')