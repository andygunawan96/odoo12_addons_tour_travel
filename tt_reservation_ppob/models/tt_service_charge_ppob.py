from odoo import api,models,fields


class TtServiceChargePPOB(models.Model):
    _inherit = "tt.service.charge"

    provider_ppob_booking_id = fields.Many2one('tt.provider.ppob', 'Provider Booking ID')

    booking_ppob_id = fields.Many2one('tt.reservation.ppob', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_ppob_ids = fields.Many2many('tt.reservation.passenger.ppob', 'tt_reservation_ppob_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger PPOB')
