from odoo import api, fields, models, _
from datetime import datetime, timedelta
import logging, traceback


class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.ppob'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger PPOB'

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_ppob_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_ppob_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.ppob', 'PPOB Inquiry')
    pax_type = fields.Selection([('ADT', 'Adult'), ('YCD', 'Senior'), ('CHD', 'Child'), ('INF', 'Infant')],
                                string='Pax Type', default='ADT')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'pax_type': self.pax_type and self.pax_type or '',
            'sale_service_charges': self.get_service_charges(),
            'service_charge_details': self.get_service_charge_details()
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res



