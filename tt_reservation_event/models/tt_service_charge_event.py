from odoo import api,models,fields


class TtServiceChargeEvent(models.Model):
    _inherit = "tt.service.charge"

    provider_event_booking_id = fields.Many2one('tt.provider.event', 'Provider ID')
    booking_event_id = fields.Many2one('tt.reservation.event', 'Booking id', ondelete="cascade", index=True, copy=False)
    passenger_event_ids = fields.Many2many('tt.reservation.passenger.event',
                                             'tt_reservation_event_cost_charge_rel', 'service_charge_id',
                                             'passenger_id', 'Passenger Event')
    # passenger_event_ids = fields.Many2many('tt.reservation.event.option', 'tt_reservation_event_cost_charge_rel', 'service_charge_id', 'option_id', 'Event Option')
    # passenger_event_ids = fields.Many2many('tt.reservation.passenger.event', 'tt_reservation_event_cost_charge_rel', 'service_charge_id', 'option_id', 'Event Option')
    # option_event_ids = fields.Many2many('tt.reservation.event.option', 'tt_reservation_event_cost_charge_rel', 'service_charge_id', 'option_id', 'Event Option')