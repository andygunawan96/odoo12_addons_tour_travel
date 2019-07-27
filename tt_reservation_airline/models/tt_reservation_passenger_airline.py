from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.airline'
    _inherit = 'tt.reservation.passenger'

    service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_airline_charge_rel', 'passenger_id', 'service_charge_id', 'Service Charges')
    booking_id = fields.Many2one('tt.reservation.airline')
    passport_number = fields.Char(string='Passport Number')
    passport_expdate = fields.Datetime(string='Passport Exp Date')

    def _compute_age(self):
        for rec in self:
            if rec.birth_date:
                d1 = datetime.strptime(str(rec.birth_date), "%Y-%m-%d").date()
                d2 = datetime.today()
                rec.age = relativedelta(d2, d1).years

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'passport_number': self.passport_number and self.passport_number or '',
            'passport_expdate': self.passport_expdate and self.passport_expdate or '',
            'sale_service_charges': self.get_service_charges()
        })
        return res

    def copy_to_passenger(self):
        res = super(TtReservationCustomer, self).copy_to_passenger()
        res.update({
            'passport_number': self.passport_number and self.passport_number or '',
            'passport_expdate': self.passport_expdate and self.passport_expdate or ''
        })
        return res

    def get_service_charges(self):
        res = []
        for rec in self.service_charge_ids:
            res.append(rec.to_dict())
        return res