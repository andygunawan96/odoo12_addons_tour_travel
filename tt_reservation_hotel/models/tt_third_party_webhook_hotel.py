from odoo import api,models,fields

class TtThirdPartyWebhook(models.Model):
    _inherit = "tt.third.party.webhook"

    booking_hotel_id = fields.Many2one('tt.reservation.hotel', 'Booking ID', ondelete='cascade', index=True, copy=False)
