from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

VARIABLE_SAMPLE_METHOD = [('nasal_swab','Nasal Swab'), ('saliva','Saliva')]

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.mitrakeluarga'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Swab Express'

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_mitrakeluarga_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')

    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_mitrakeluarga_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')

    booking_id = fields.Many2one('tt.reservation.mitrakeluarga', 'Booking')

    email = fields.Char('Email')
    address_ktp = fields.Char('Address KTP')
    phone_number = fields.Char('Phone Number')

    # provinsi = fields.Char('Pronvinsi')
    # kabupaten = fields.Char('Kabupaten')
    # kecamatan = fields.Char('Kecamatan')
    # kelurahan = fields.Char('Kelurahan')

    # sample_method = fields.Selection(VARIABLE_SAMPLE_METHOD,'Sample Method')
    is_ticketed = fields.Boolean('Ticketed')
    ticket_number = fields.Char('Ticket Number')
    result_url = fields.Char('Result Url')

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        sale_service_charges = self.get_service_charges()
        pax_type = ''
        for pnr in sale_service_charges:
            for svc in sale_service_charges[pnr]:
                pax_type = sale_service_charges[pnr][svc]['pax_type']
                break
            break
        res.update({
            'sale_service_charges': sale_service_charges,
            'service_charge_details': self.get_service_charge_details(),
            'pax_type': pax_type,
            'email': self.email,
            'phone_number': self.phone_number,
            'result_url': self.result_url,
            'ticket_number': self.ticket_number,
            'address_ktp': self.address_ktp
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res




