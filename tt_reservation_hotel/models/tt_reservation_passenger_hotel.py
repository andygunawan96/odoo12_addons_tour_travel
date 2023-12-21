from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.hotel'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Hotel'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_hotel_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_hotel_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')
    # fee_ids = fields.One2many('tt.fee.airline', 'passenger_id', 'SSR')
    booking_id = fields.Many2one('tt.reservation.hotel')
    room_id = fields.Many2one('tt.hotel.reservation.details')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        fee_list = []
        # for rec in self.fee_ids:
        #     fee_list.append(rec.to_dict())
        sale_service_charges = self.get_service_charges()
        service_charge_details = self.get_service_charge_details()
        res.update({
            'sale_service_charges': sale_service_charges,
            'service_charge_details': service_charge_details,
            'fees': fee_list
        })
        # if len(self.channel_service_charge_ids.ids)>0:
        #     res['channel_service_charges'] = self.get_channel_service_charges()
        return res

    # def create_ssr(self,ssr_param,pnr,provider_id):
        # Tmbahan lain sperti breakfast, free ticket activity or etc
        # return True





