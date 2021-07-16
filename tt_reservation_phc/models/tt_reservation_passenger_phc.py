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

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)

    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_phc_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')

    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_phc_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')

    booking_id = fields.Many2one('tt.reservation.phc', 'Booking')

    result_url = fields.Char('Result URL')
    verify = fields.Boolean('Verify Data', default=False)
    label_url = fields.Char('Label URL')

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

    pcr_data = fields.Text('PCR Data')
    is_ticketed = fields.Boolean('Ticketed')
    ticket_number = fields.Char('Ticket Number')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.reservation.passenger.phc')
        return super(TtReservationCustomer, self).create(vals_list)

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()
        res.update({
            'result_url': self.result_url,
            'label_url': self.label_url,
            'verify': self.verify,
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
            'phone_number': self.phone_number,
            'pcr_data': self.pcr_data and json.loads(self.pcr_data) or self.pcr_data,
            'nationality_name': self.nationality_id.name,
            'ticket_number': self.ticket_number
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res

    ## find duplicate passenger that has been sent to PHC but not yet verified
    def find_duplicate_passenger_new_order(self,pax_list,carrier_code):
        error_log = ''
        error_log_indo = ''
        for psg in pax_list:
            duplicate_pax_list = self.search([('identity_number','=',psg['identity']['identity_number']),
                                              ('booking_id.state_vendor','=','new_order'),
                                              ('booking_id.carrier_name','=',carrier_code)])
            if duplicate_pax_list:
                if error_log == '':
                    error_log_indo += '<br/>\nNomor identitas sama dengan booking lain<br/>\n'
                    error_log += '<br/>\nDuplicate Identity Number with other bookings<br/>\n'
                error_log_indo += 'Pelanggan #%s <br/>\nNama: %s %s %s <br/>\nNomor identitas: %s<br/><br/>\n\n' % (psg['sequence']+1, psg['title'], psg['first_name'], psg['last_name'], psg['identity']['identity_number'])
                error_log += 'Passenger #%s <br/>\nName: %s %s %s <br/>\nIdentity Number: %s<br/><br/>\n\n' % (psg['sequence']+1, psg['title'], psg['first_name'], psg['last_name'], psg['identity']['identity_number'])
        if error_log_indo:
            error_log_indo += error_log
        return error_log_indo

    def fill_seq_id(self):
        for idx,rec in enumerate(self.search([('seq_id','=',False)])):
            rec.seq_id = "PGH.O%s%s" % (idx,datetime.now().second)