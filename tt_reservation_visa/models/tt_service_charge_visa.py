from odoo import api, models, fields


class ServiceChargeVisa(models.Model):
    _inherit = "tt.service.charge"

    visa_id = fields.Many2one('tt.reservation.visa', 'Visa', ondelete='cascade', index=True, copy=False)

    pricelist_id = fields.Many2one('tt.reservation.visa.pricelist', 'Pricelist Visa')

    passenger_visa_ids = fields.Many2many('tt.reservation.visa.order.passengers', 'tt_reservation_visa_cost_charge_rel',
                                          'service_charge_id', 'passenger_id', 'Passenger Visa', readonly=False)

    provider_visa_booking_id = fields.Many2one('tt.provider.visa', 'Booking')
