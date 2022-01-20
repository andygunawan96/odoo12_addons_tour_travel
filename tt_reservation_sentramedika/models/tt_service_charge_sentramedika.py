from odoo import api,models,fields

class TtServiceChargeSentraMedika(models.Model):
    _inherit = "tt.service.charge"

    provider_sentramedika_booking_id = fields.Many2one('tt.provider.sentramedika', 'Provider Booking ID')

    booking_sentramedika_id = fields.Many2one('tt.reservation.sentramedika', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_sentramedika_ids = fields.Many2many('tt.reservation.passenger.sentramedika', 'tt_reservation_sentramedika_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Sentra Medika')
