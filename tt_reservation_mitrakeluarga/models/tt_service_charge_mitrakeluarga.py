from odoo import api,models,fields

class TtServiceChargeMitraKeluarga(models.Model):
    _inherit = "tt.service.charge"

    provider_mitrakeluarga_booking_id = fields.Many2one('tt.provider.mitrakeluarga', 'Provider Booking ID')

    booking_mitrakeluarga_id = fields.Many2one('tt.reservation.mitrakeluarga', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_mitrakeluarga_ids = fields.Many2many('tt.reservation.passenger.mitrakeluarga', 'tt_reservation_mitrakeluarga_cost_charge_rel', 'service_charge_id', 'passenger_id', 'Passenger Swab Express')
