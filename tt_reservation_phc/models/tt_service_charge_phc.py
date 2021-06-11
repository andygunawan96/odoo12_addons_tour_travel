from odoo import api,models,fields

class TtServiceChargephc(models.Model):
    _inherit = "tt.service.charge"

    provider_phc_booking_id = fields.Many2one('tt.provider.phc', 'Provider Booking ID')

    booking_phc_id = fields.Many2one('tt.reservation.phc', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_phc_ids = fields.Many2many('tt.reservation.passenger.phc', 'tt_reservation_phc_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger phc')
