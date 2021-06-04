from odoo import api,models,fields

class TtServiceChargePeriksain(models.Model):
    _inherit = "tt.service.charge"

    provider_periksain_booking_id = fields.Many2one('tt.provider.periksain', 'Provider Booking ID')

    booking_periksain_id = fields.Many2one('tt.reservation.periksain', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_periksain_ids = fields.Many2many('tt.reservation.passenger.periksain', 'tt_reservation_periksain_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Periksain')