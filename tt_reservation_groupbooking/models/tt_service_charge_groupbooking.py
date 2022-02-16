from odoo import api, models, fields


class ServiceChargeGroupBooking(models.Model):
    _inherit = "tt.service.charge"

    provider_groupbooking_booking_id = fields.Many2one('tt.provider.groupbooking', 'Provider Booking ID')

    paxprice_groupbooking_booking_id = fields.Many2one('tt.paxprice.groupbooking', 'Pax Price ID')

    booking_groupbooking_id = fields.Many2one('tt.reservation.groupbooking', 'Booking', ondelete='cascade', index=True, copy=False)

    passenger_groupbooking_ids = fields.Many2many('tt.reservation.passenger.groupbooking',
                                             'tt_reservation_groupbooking_cost_charges_rel', 'service_charge_id', 'passenger_id',
                                             'Passenger groupbooking', readonly=False)
