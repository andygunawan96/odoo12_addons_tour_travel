from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.insurance'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Insurance'

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_insurance_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_insurance_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.insurance')
    is_ticketed = fields.Boolean('Ticketed')
    account_number = fields.Char('Passenger Account Number')
    account_name = fields.Char('Passenger Account Name')
    passport_type = fields.Selection(variables.IDENTITY_TYPE, 'Passport Type')
    passport_number = fields.Char('Passport Number')
    passport_expdate = fields.Date('Passport Expire Date')
    passport_country_of_issued_id = fields.Many2one('res.country', 'Passport Issued Country')
    insurance_data = fields.Text('Insurance Data')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.reservation.passenger.insurance')
        return super(TtReservationCustomer, self).create(vals_list)

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'sale_service_charges': self.get_service_charges(),
            'passport_type': self.passport_type and self.passport_type or '',
            'passport_number': self.passport_number and self.passport_number or '',
            'passport_expdate': self.passport_expdate and self.passport_expdate.strftime('%Y-%m-%d'),
            'passport_country_of_issued_id': self.passport_country_of_issued_id and self.passport_country_of_issued_id.code or '',
            'insurance_data': self.insurance_data and json.loads(self.insurance_data) or {},
            'seq_id': self.seq_id
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res

    def fill_seq_id(self):
        for idx,rec in enumerate(self.search([('seq_id','=',False)])):
            rec.seq_id = "PGI.O%s%s" % (idx,datetime.now().second)
