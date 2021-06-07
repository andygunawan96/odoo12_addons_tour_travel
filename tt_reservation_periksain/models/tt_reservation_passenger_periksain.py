from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.periksain'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Periksain'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_periksain_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')

    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_periksain_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')

    booking_id = fields.Many2one('tt.reservation.periksain', 'Booking')

    email = fields.Char('Email')

    phone_number = fields.Char('Phone Number')

    sample_method = fields.Selection([('nasal_swab','Nasal Swab'),
                                      ('saliva','Saliva')],'Sample Method')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'sale_service_charges': self.get_service_charges(),
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res




