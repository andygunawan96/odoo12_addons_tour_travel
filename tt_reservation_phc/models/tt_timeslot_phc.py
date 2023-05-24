import pytz

from odoo import api,models,fields, _
from ...tools import util,variables,ERR
import logging,traceback
from datetime import datetime,date, timedelta

_logger = logging.getLogger(__name__)
#HC Homecare, DT Drive Thru
COMMISSION_PER_PAX_ANTIGEN = 11600 ## komisi agent /pax
COMMISSION_PER_PAX_PCR_HC = 75000 ## komisi agent /pax
COMMISSION_PER_PAX_PCR_DT = 24000 ## komisi agent /pax
COMMISSION_PER_PAX_PCR_DT_PRIORITY = 60000 ## komisi agent /pax
COMMISSION_PER_PAX_PCR_DT_EXPRESS = 300000 ## komisi agent /pax
COMMISSION_PER_PAX_PCR_DT_SRBD = 18000 ## komisi agent /pax
BASE_PRICE_PER_PAX_ANTIGEN = 99000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR_HC = 750000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR_DT = 275000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR_DT_PRIORITY = 550000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR_DT_EXPRESS = 1800000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR_DT_SRBD = 195000 ## harga 1 /pax
SINGLE_SUPPLEMENT = 25000 ## 1 orang
OVERTIME_SURCHARGE = 50000 ## lebih dari 18.00 /pax
ADMIN_FEE_ANTIGEN_DRIVETHRU = 10000
ADMIN_FEE_PCR_DRIVETHRU = 10000

class TtTimeslotphc(models.Model):
    _name = 'tt.timeslot.phc'
    _description = 'Orbis Model Timeslot phc'
    _order = 'datetimeslot,id'
    _rec_name = 'timeslot_display_name'

    seq_id = fields.Char('Sequence ID', readonly=True)

    dateslot = fields.Date('Dateslot')

    datetimeslot = fields.Datetime('DateTime Slot')
    datetimeslot_end = fields.Datetime('DateTime Slot End')

    timeslot_display_name = fields.Char('Display Name', compute="_compute_timeslot_display_name")
    timeslot_type = fields.Selection([('home_care', 'Home Care'), ('drive_thru', 'Drive Thru'), ('group_booking', 'Group Booking')], 'Timeslot Type')

    destination_id = fields.Many2one('tt.destinations','Area')
    destination_area = fields.Selection([('surabaya_all','Surabaya All'),
                                         ('surabaya_pusat','Surabaya Pusat'),
                                         ('surabaya_timur','Surabaya Timur'),
                                         ('surabaya_selatan','Surabaya Selatan'),
                                         ('surabaya_barat','Surabaya Barat'),
                                         ('surabaya_utara','Surabaya Utara')],default='surabaya_all')

    selected_count = fields.Integer('Selected Counter',compute="_compute_selected_counter",store=True)

    used_count = fields.Integer('Used Counter',compute="_compute_used_counter",store=True)#used reservation count
    used_adult_count = fields.Integer('Used Adult Counter', compute="_compute_used_counter", store=True)#used adult count
    used_pcr_count = fields.Integer('Used PCR Counter', compute="_compute_used_counter", store=True)#used PCR count
    used_pcr_issued_count = fields.Integer('Used PCR Issued Counter', compute="_compute_used_counter", store=True)#used PCR count

    max_book_datetime = fields.Datetime('Max Book Datetime', required=True, default=fields.Datetime.now)

    booking_ids = fields.Many2many('tt.reservation.phc','tt_reservation_phc_timeslot_rel', 'timeslot_id', 'booking_id', 'Selected on By Customer Booking(s)')

    booking_used_ids = fields.One2many('tt.reservation.phc','picked_timeslot_id', 'Confirmed to Customer Booking(s)')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    commission_antigen = fields.Monetary('Commission per PAX Antigen')
    commission_pcr = fields.Monetary('Commission per PAX PCR')
    commission_pcr_priority = fields.Monetary('Commission per PAX PCR Priority')
    commission_pcr_express = fields.Monetary('Commission per PAX PCR Express')
    commission_srbd = fields.Monetary('Commission per PAX S-RBD')

    base_price_antigen = fields.Monetary('Base Price per PAX Antigen')
    base_price_pcr = fields.Monetary('Base Price per PAX PCR')
    base_price_pcr_priority = fields.Monetary('Base Price per PAX PCR Priority')
    base_price_pcr_express = fields.Monetary('Base Price per PAX PCR Express')
    base_price_srbd = fields.Monetary('Base Price per PAX S-RBD')

    single_supplement = fields.Monetary('Single Supplement')
    overtime_surcharge = fields.Monetary('Overtime Surcharge')
    admin_fee_antigen_drivethru = fields.Monetary('Admin Fee Antigen DriveThru')
    admin_fee_pcr_drivethru = fields.Monetary('Admin Fee PCR DriveThru')

    total_timeslot = fields.Integer('Max Timeslot', required=True, default=5)##reservation count
    total_adult_timeslot = fields.Integer('Max Adult Timeslot', required=True, default=420)##adult count
    total_pcr_timeslot = fields.Integer('Max PCR Timeslot', required=True, default=195)##pcr count

    active = fields.Boolean('Active', default='True')

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    agent_id = fields.Many2one('tt.agent', 'Agent')

    @api.depends('datetimeslot')
    def _compute_timeslot_display_name(self):
        for rec in self:
            if rec.timeslot_type != 'drive_thru':
                rec.timeslot_display_name = str(rec.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')))[:19]
            else:
                rec.timeslot_display_name = str(rec.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')))[:19]

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.timeslot.phc')
        return super(TtTimeslotphc, self).create(vals_list)

    @api.depends('booking_ids')
    def _compute_selected_counter(self):
        for rec in self:
            rec.selected_count = len(rec.booking_ids.ids)

    @api.depends('booking_used_ids','booking_used_ids.state')
    def _compute_used_counter(self):
        for rec in self:
            used_count = 0
            adult_count = 0
            pcr_count = 0
            pcr_issued_count = 0
            for rec2 in rec.booking_used_ids.filtered(lambda x: x.state in ['booked', 'issued']):
                used_count += 1
                adult_count += rec2.adult
                if 'PCR' in rec2.carrier_name:
                    pcr_count += rec2.adult
                    if rec2.state == 'issued':
                        pcr_issued_count += rec2.adult
            if used_count != rec.used_count:
                rec.used_count = used_count
            if rec.used_adult_count != adult_count:
                rec.used_adult_count = adult_count
            if rec.used_pcr_count != pcr_count:
                rec.used_pcr_count = pcr_count
            if rec.used_pcr_issued_count != pcr_issued_count:
                rec.used_pcr_issued_count = pcr_issued_count



    def mass_close_timeslot(self):
        for rec in self:
            rec.total_timeslot = 0
            rec.total_adult_timeslot = 0
            rec.total_pcr_timeslot = 0
    # {
    #     "max_date": "2021-06-20",
    #     "timeslots": {
    #         "Surabaya": {
    #              "2021-06-05": [
    #             {
    #                 "time": "08:00",
    #                 "seq_id": "TSP.020202"
    #             },
    #             {
    #                 "time": "08:40",
    #                 "seq_id": "TSP.020203"
    #             }
    #         ]
    #         }
    #     }
    # }

    def get_available_timeslot_api(self, req, context):
        current_wib_datetime = datetime.now(pytz.timezone('Asia/Jakarta'))
        current_datetime = current_wib_datetime.astimezone(pytz.utc)
        carrier_obj = self.env['tt.transport.carrier'].search([('code','=',req['carrier_code'])],limit=1)

        dom = ['|', ('agent_id', '=', False), ('agent_id', '=', context['co_agent_id'])]

        if carrier_obj.id in [self.env.ref('tt_reservation_phc.tt_transport_carrier_phc_home_care_antigen').id,
                          self.env.ref('tt_reservation_phc.tt_transport_carrier_phc_home_care_pcr').id]:
            dom.append(('timeslot_type', 'in', ['home_care', 'group_booking']))
            # if '06:00' < str(current_wib_datetime.time())[:5] < '14:00':
            #     dom.append(('datetimeslot', '>=', datetime.now(pytz.utc) + timedelta(hours=2)))
            # else:
            #     min_datetime = current_datetime.replace(hour=1, minute=0, second=0, microsecond=0)
            #     if current_datetime > min_datetime:
            #         min_datetime = min_datetime + timedelta(days=1)
            #     dom.append(('datetimeslot', '>=', min_datetime))

            # home care di ganti H+1
            if current_wib_datetime <= current_wib_datetime.replace(hour=17, minute=0, second=0, microsecond=0):#kalau sblm jam 5 sore utk H+1
                dom.append(('datetimeslot', '>=', current_wib_datetime.replace(hour=0,minute=0,second=0,microsecond=0) + timedelta(days=1)))
            else:#stlh jam 5 sore utk H+2
                dom.append(('datetimeslot', '>=', current_wib_datetime.replace(hour=0,minute=0,second=0,microsecond=0) + timedelta(days=2)))
        else:
            dom.append(('timeslot_type', '=', 'drive_thru'))
            ## kalau kurang dari jam 16.00 di tambah timedelta 0 else di tambah 1 hari
            # dom.append(('dateslot', '>=', datetime.today() if current_wib_datetime <= current_wib_datetime.replace(hour=14,minute=30,second=0,microsecond=0) else datetime.today() + timedelta(days=1)))
            dom.append(('max_book_datetime', '>=', datetime.now(pytz.utc)))
            dom.append(('total_timeslot','>',0))

        timeslots = self.search(dom)
        # max_date = date.today()
        timeslot_dict = {}
        for rec in timeslots:
            if rec.destination_id.name not in timeslot_dict:
                timeslot_dict[rec.destination_id.name] = {
                    'max_date': str(date.today()),
                    'min_date': str(date.max),
                    'timeslots': {}
                }
            str_dateslot = str(rec.dateslot)
            if str_dateslot > timeslot_dict[rec.destination_id.name]['max_date']:
                timeslot_dict[rec.destination_id.name]['max_date'] = str_dateslot
            if str_dateslot < timeslot_dict[rec.destination_id.name]['min_date']:
                timeslot_dict[rec.destination_id.name]['min_date'] = str_dateslot

            if str_dateslot not in timeslot_dict[rec.destination_id.name]['timeslots']:
                timeslot_dict[rec.destination_id.name]['timeslots'][str_dateslot] = []

            timeslot_dict[rec.destination_id.name]['timeslots'][str_dateslot].append({
                'time': str(rec.datetimeslot)[11:16],
                'time_end': str(rec.datetimeslot_end)[11:16],
                'subarea': rec.destination_area,
                'seq_id': rec.seq_id,
                'availability': rec.get_availability(carrier_obj.code),
                'group_booking': True if rec.agent_id else False,
                "total_pcr_issued_timeslot": 200,
                "used_pcr_issued_count": rec.used_pcr_issued_count
            })
        return ERR.get_no_error(timeslot_dict)

    def get_availability(self,carrier_code,adult_count=1):
        ## availability adult & pcr
        availability = self.used_adult_count + adult_count <= self.total_adult_timeslot

        if 'PCR' in carrier_code:
            availability = availability and self.used_pcr_count + adult_count <= self.total_pcr_timeslot and self.used_pcr_issued_count + adult_count <= 175

        if self.timeslot_type == 'drive_thru':
            return availability
        else:
            return (self.used_count < self.total_timeslot) and availability

    def get_datetimeslot_str(self):
        if self.datetimeslot:
            if self.timeslot_type != 'drive_thru':
                return self.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')).strftime('%d %B %Y %H:%M')
            else:
                return '%s (08:00 - 15:00 WIB)' % (self.datetimeslot.strftime('%d %B %Y'))
        else:
            return 'Date/Time is not specified.'

    def to_dict(self):
        return {
            "datetimeslot": self.datetimeslot.strftime('%Y-%m-%d %H:%M'),
            "datetimeslot_end": self.datetimeslot.strftime('%Y-%m-%d %H:%M'),
            "area": self.destination_id.city,
            "subarea": self.destination_area,
            "total_pcr_timeslot": self.total_pcr_timeslot,
            "used_pcr_count": self.used_pcr_count,
            "total_pcr_issued_timeslot": 200,
            "used_pcr_issued_count": self.used_pcr_issued_count
        }


class TtTimeslotphcdefault(models.Model):
    _name = 'tt.timeslot.phc.default'
    _description = 'Orbis Model Timeslot PHC Default'
    _order = 'sequence'

    name = fields.Char("Name", required=True)
    sequence = fields.Integer("Sequence",default=200)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    commission_antigen = fields.Monetary('Commission per PAX Antigen', default=COMMISSION_PER_PAX_ANTIGEN,
                                         required=True)
    commission_pcr = fields.Monetary('Commission per PAX PCR', default=COMMISSION_PER_PAX_PCR_HC, required=True)
    commission_pcr_dt = fields.Monetary('Commission per PAX PCR DT', default=COMMISSION_PER_PAX_PCR_DT, required=True)
    commission_pcr_priority = fields.Monetary('Commission per PAX PCR Priority',
                                             default=COMMISSION_PER_PAX_PCR_DT_PRIORITY, required=True)
    commission_pcr_express = fields.Monetary('Commission per PAX PCR Express',
                                             default=COMMISSION_PER_PAX_PCR_DT_EXPRESS, required=True)
    commission_srbd = fields.Monetary('Commission per PAX S-RBD',
                                             default=COMMISSION_PER_PAX_PCR_DT_SRBD, required=True)

    base_price_antigen = fields.Monetary('Base Price per PAX Antigen', default=BASE_PRICE_PER_PAX_ANTIGEN,
                                         required=True)
    base_price_pcr = fields.Monetary('Base Price per PAX PCR', default=BASE_PRICE_PER_PAX_PCR_HC, required=True)
    base_price_pcr_dt = fields.Monetary('Base Price per PAX PCR DT', default=BASE_PRICE_PER_PAX_PCR_DT, required=True)
    base_price_pcr_priority = fields.Monetary('Base Price per PAX PCR Priority',
                                              default=BASE_PRICE_PER_PAX_PCR_DT_PRIORITY, required=True)
    base_price_pcr_express = fields.Monetary('Base Price per PAX PCR Express',
                                             default=BASE_PRICE_PER_PAX_PCR_DT_EXPRESS, required=True)
    base_price_srbd = fields.Monetary('Base Price per PAX S-RBD',
                                             default=BASE_PRICE_PER_PAX_PCR_DT_SRBD, required=True)

    single_supplement = fields.Monetary('Single Supplement', default=SINGLE_SUPPLEMENT, required=True)
    overtime_surcharge = fields.Monetary('Overtime Surcharge', default=OVERTIME_SURCHARGE, required=True)

    admin_fee_antigen_drivethru = fields.Monetary('Admin Fee Antigen DriveThru')
    admin_fee_pcr_drivethru = fields.Monetary('Admin Fee PCR DriveThru')