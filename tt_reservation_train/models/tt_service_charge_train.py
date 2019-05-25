from odoo import api,models,fields

class ServiceChargeTrain(models.Model):
    _inherit = "tt.service.charge"

    provider_train_booking_id = fields.Many2one('tt.tb.provider.train', 'Provider Booking ID')

    booking_train_id = fields.Many2one('tt.reservation.train', 'Booking', ondelete='cascade', index=True, copy=False)
