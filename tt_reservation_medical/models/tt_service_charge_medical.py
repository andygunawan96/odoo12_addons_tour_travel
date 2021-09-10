from odoo import api,models,fields

class TtServiceChargemedical(models.Model):
    _inherit = "tt.service.charge"

    provider_medical_booking_id = fields.Many2one('tt.provider.medical', 'Provider Booking ID')

    booking_medical_id = fields.Many2one('tt.reservation.medical', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_medical_ids = fields.Many2many('tt.reservation.passenger.medical', 'tt_reservation_medical_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger medical')
