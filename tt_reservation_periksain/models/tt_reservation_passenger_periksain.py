from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

VARIABLE_SAMPLE_METHOD = [('nasal_swab','Nasal Swab'), ('saliva','Saliva')]

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.periksain'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Periksain'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_periksain_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')

    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_periksain_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')

    booking_id = fields.Many2one('tt.reservation.periksain', 'Booking')

    email = fields.Char('Email')
    address = fields.Char('Address')
    phone_number = fields.Char('Phone Number')

    provinsi = fields.Char('Pronvinsi')
    kabupaten = fields.Char('Kabupaten')
    kecamatan = fields.Char('Kecamatan')
    kelurahan = fields.Char('Kelurahan')

    sample_method = fields.Selection(VARIABLE_SAMPLE_METHOD,'Sample Method')
    is_ticketed = fields.Boolean('Ticketed')
    ticket_number = fields.Char('Ticket Number')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        for rec in VARIABLE_SAMPLE_METHOD:
            if rec[0] == self.sample_method:
                sample_method = rec[1]
        res.update({
            'sale_service_charges': self.get_service_charges(),
            'address': self.address,
            'provinsi': self.provinsi,
            'kabupaten': self.kabupaten,
            'kecamatan': self.kecamatan,
            'kelurahan': self.kelurahan,
            'sample_method': sample_method,
            'sample_method_code': self.sample_method,
            'email': self.email,
            'phone_number': self.phone_number
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res




