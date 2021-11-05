from odoo import api,models,fields

class TtServiceChargeInsurance(models.Model):
    _inherit = "tt.service.charge"

    provider_insurance_booking_id = fields.Many2one('tt.provider.insurance', 'Provider Booking ID')

    booking_insurance_id = fields.Many2one('tt.reservation.insurance', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_insurance_ids = fields.Many2many('tt.reservation.passenger.insurance', 'tt_reservation_insurance_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Insurance')