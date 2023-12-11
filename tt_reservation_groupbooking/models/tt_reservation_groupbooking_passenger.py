from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.groupbooking'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Group Booking'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_groupbooking_cost_charges_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_groupbooking_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.groupbooking')
    pax_type = fields.Selection([('ADT', 'Adult'), ('CHD', 'Child'), ('INF', 'Infant')])
    is_ticketed = fields.Boolean('Ticketed')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'sale_service_charges': self.get_service_charges(),
            'service_charge_details': self.get_service_charge_details(),
            'pax_type': self.pax_type
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res




