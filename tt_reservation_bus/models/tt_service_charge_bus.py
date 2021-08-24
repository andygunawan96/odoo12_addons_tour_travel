from odoo import api,models,fields

class TtServiceChargeBus(models.Model):
    _inherit = "tt.service.charge"

    provider_bus_booking_id = fields.Many2one('tt.provider.bus', 'Provider Booking ID')

    booking_bus_id = fields.Many2one('tt.reservation.bus', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_bus_ids = fields.Many2many('tt.reservation.passenger.bus', 'tt_reservation_bus_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Bus')