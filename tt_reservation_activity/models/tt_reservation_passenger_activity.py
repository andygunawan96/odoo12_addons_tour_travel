from odoo import api, fields, models, _
from datetime import datetime, timedelta
import logging, traceback


class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.activity'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Activity'

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_activity_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_activity_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.activity', 'Activity Booking')
    pax_type = fields.Selection([('ADT', 'Adult'), ('YCD', 'Senior'), ('CHD', 'Child'), ('INF', 'Infant')],
                                string='Pax Type')
    activity_sku_id = fields.Many2one('tt.master.activity.sku', 'Activity SKU')
    option_ids = fields.One2many('tt.reservation.passenger.activity.option', 'activity_passenger_id', 'Options')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'pax_type': self.pax_type and self.pax_type or '',
            'sku_name': self.activity_sku_id and self.activity_sku_id.title or '',
            'sale_service_charges': self.get_service_charges(),
            'service_charge_details': self.get_service_charge_details()
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res


class TtActivityPassengerOption(models.Model):
    _name = 'tt.reservation.passenger.activity.option'
    _description = 'Reservation Passenger Activity Option'

    name = fields.Char('Information')
    value = fields.Char('Value')
    description = fields.Text('Description')
    activity_passenger_id = fields.Many2one('tt.reservation.passenger.activity', 'Activity Passenger')


