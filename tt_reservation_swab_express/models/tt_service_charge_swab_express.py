from odoo import api,models,fields

class TtServiceChargeSwabExpress(models.Model):
    _inherit = "tt.service.charge"

    provider_swab_express_booking_id = fields.Many2one('tt.provider.swab.express', 'Provider Booking ID')

    booking_swab_express_id = fields.Many2one('tt.reservation.swab.express', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_swab_express_ids = fields.Many2many('tt.reservation.passenger.swab.express', 'tt_reservation_swab_express_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Swab Express')
