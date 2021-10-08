from odoo import api,models,fields

class TtServiceChargeLabPintar(models.Model):
    _inherit = "tt.service.charge"

    provider_lab_pintar_booking_id = fields.Many2one('tt.provider.lab.pintar', 'Provider Booking ID')

    booking_lab_pintar_id = fields.Many2one('tt.reservation.lab.pintar', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_lab_pintar_ids = fields.Many2many('tt.reservation.passenger.lab.pintar', 'tt_reservation_lab_pintar_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Lab Pintar')
