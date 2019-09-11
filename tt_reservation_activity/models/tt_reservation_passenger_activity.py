from odoo import api, fields, models, _
from datetime import datetime, timedelta
import logging, traceback


class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.activity'
    _inherit = 'tt.reservation.passenger'
    _description = 'Rodex Model'

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_activity_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_activity_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.activity', 'Activity Booking')
    pax_type = fields.Selection([('ADT', 'Adult'), ('YCD', 'Senior'), ('CHD', 'Child'), ('INF', 'Infant')],
                                string='Pax Type')
    activity_sku_id = fields.Many2one('tt.master.activity.sku', 'Activity SKU')
    api_data = fields.Text('API Data')



