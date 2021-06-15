from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

VARIABLE_SAMPLE_METHOD = [('nasal_swab','Nasal Swab'), ('saliva','Saliva')]

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.phc'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger phc'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_phc_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')

    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_phc_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')

    booking_id = fields.Many2one('tt.reservation.phc', 'Booking')

    email = fields.Char('Email')

    phone_number = fields.Char('Phone Number')

    tempat_lahir = fields.Char('Tempat Lahir')
    profession = fields.Char('Profession')
    work_place = fields.Char('Work Place')
    address = fields.Char('Address')
    rt = fields.Char('RT')
    rw = fields.Char('RW')
    kabupaten = fields.Char('Kabupaten')
    kecamatan = fields.Char('Kecamatan')
    kelurahan = fields.Char('Kelurahan')
    address_ktp = fields.Char('Address KTP')
    rt_ktp = fields.Char('RT KTP')
    rw_ktp = fields.Char('RW KTP')
    kabupaten_ktp = fields.Char('Kabupaten KTP')
    kecamatan_ktp = fields.Char('Kecamatan KTP')
    kelurahan_ktp = fields.Char('Kelurahan KTP')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'sale_service_charges': self.get_service_charges(),
            'tempat_lahir': self.tempat_lahir,
            'profession': self.profession,
            'work_place': self.work_place,
            'address': self.address,
            'rt': self.rt,
            'rw': self.rw,
            'kabupaten': self.kabupaten,
            'kecamatan': self.kecamatan,
            'kelurahan': self.kelurahan,
            'address_ktp': self.address_ktp,
            'rt_ktp': self.rt_ktp,
            'rw_ktp': self.rw_ktp,
            'kabupaten_ktp': self.kabupaten_ktp,
            'kecamatan_ktp': self.kecamatan_ktp,
            'kelurahan_ktp': self.kelurahan_ktp,
            'email': self.email,
            'phone_number': self.phone_number
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res




