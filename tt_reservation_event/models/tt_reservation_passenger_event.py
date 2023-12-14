from odoo import api, fields, models, _
from datetime import datetime, timedelta
import logging, traceback


class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.event'
    _inherit = 'tt.reservation.passenger'
    _description = 'Orbis Event Model'

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_event_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_event_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.event', 'Event Booking')
    provider_id = fields.Many2one('tt.provider.event', 'Provider')
    pax_type = fields.Selection([('ADT', 'Adult'), ('YCD', 'Senior'), ('CHD', 'Child'), ('INF', 'Infant')],
                                string='Pax Type')
    option_id = fields.Many2one('tt.reservation.event.option', 'Options')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'pax_type': self.pax_type and self.pax_type or '',
            'sale_service_charges': self.get_service_charges(),
            'service_charge_details': self.get_service_charge_details(),
            'option': self.option_id.to_dict(),
        })
        if len(self.channel_service_charge_ids.ids) > 0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res
