from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.airline'
    _inherit = 'tt.reservation.passenger'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_airline_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_airline_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.airline')
    passport_number = fields.Char(string='Passport Number')
    passport_expdate = fields.Datetime(string='Passport Exp Date')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'passport_number': self.passport_number and self.passport_number or '',
            'passport_expdate': self.passport_expdate and self.passport_expdate or '',
            'sale_service_charges': self.get_service_charges()
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res

    def copy_to_passenger(self):
        res = super(TtReservationCustomer, self).copy_to_passenger()
        res.update({
            'passport_number': self.passport_number and self.passport_number or '',
            'passport_expdate': self.passport_expdate and self.passport_expdate or ''
        })
        return res

