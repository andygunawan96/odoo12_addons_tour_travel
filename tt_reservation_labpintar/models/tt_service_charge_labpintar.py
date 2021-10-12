from odoo import api,models,fields

class TtServiceChargeLabPintar(models.Model):
    _inherit = "tt.service.charge"

    provider_labpintar_booking_id = fields.Many2one('tt.provider.labpintar', 'Provider Booking ID')

    booking_labpintar_id = fields.Many2one('tt.reservation.labpintar', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_labpintar_ids = fields.Many2many('tt.reservation.passenger.labpintar', 'tt_reservation_labpintar_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Lab Pintar')
