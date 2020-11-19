from odoo import api, models, fields


class ServiceChargePassport(models.Model):
    _inherit = "tt.service.charge"

    passport_id = fields.Many2one('tt.reservation.passport', 'Passport', ondelete='cascade', index=True, copy=False)

    passport_pricelist_id = fields.Many2one('tt.reservation.passport.pricelist', 'Pricelist Passport')

    passenger_passport_ids = fields.Many2many('tt.reservation.passport.order.passengers',
                                              'tt_reservation_passport_cost_charge_rel', 'service_charge_id', 'passenger_id',
                                              'Passenger Passport', readonly=False)

    provider_passport_booking_id = fields.Many2one('tt.provider.passport', 'Booking')
