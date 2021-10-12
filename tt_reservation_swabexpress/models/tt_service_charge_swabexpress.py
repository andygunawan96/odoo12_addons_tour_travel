from odoo import api,models,fields

class TtServiceChargeSwabExpress(models.Model):
    _inherit = "tt.service.charge"

    provider_swabexpress_booking_id = fields.Many2one('tt.provider.swabexpress', 'Provider Booking ID')

    booking_swabexpress_id = fields.Many2one('tt.reservation.swabexpress', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_swabexpress_ids = fields.Many2many('tt.reservation.passenger.swabexpress', 'tt_reservation_swabexpress_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Swab Express')
