import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)

COMMISSION_PER_PAX = 22000 ## komisi agent /pax
COMMISSION_PER_PAX_PCR = 50000 ## komisi agent /pax
BASE_PRICE_PER_PAX = 150000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR = 650000 ## harga 1 /pax
SINGLE_SUPPLEMENT = 25000 ## 1 orang
OVERTIME_SURCHARGE = 50000 ## lebih dari 18.00 /pax
CITO_SURCHARGE = 25000## Urgent cito surcharge range 2-5jam stlh jam book

class CreateTimeslotMitraKeluargaWizard(models.TransientModel):
    _name = "create.timeslot.mitrakeluarga.wizard"
    _description = 'Swab Express Create Timeslot Wizard'

    start_date = fields.Date('Start Date',required=True, default=fields.Date.context_today)
    end_date = fields.Date('End Date',required=True, default=fields.Date.context_today)
    time_string = fields.Text('Time',default='08:00,09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,19:00')

    id_time_vendor = fields.Text('ID Time Vendor', default='')
    id_jenis_tindakan_vendor = fields.Text('ID Jenis Tindakan Vendor', default='')

    timeslot_type = fields.Selection([('home_care', 'Home Care'), ('group_booking', 'Group Booking')], 'Timeslot Type', default='home_care',
                                     required=True)
    total_timeslot = fields.Integer('Total Timeslot', default=5, required=True)

    antigen_price_ids = fields.Many2many('tt.price.list.mitrakeluarga', 'tt_price_list_mitrakeluarga_price_wizard_antigen_rel','timeslot_antigen_wizard_id', 'price_list_id', 'Antigen')

    pcr_price_ids = fields.Many2many('tt.price.list.mitrakeluarga', 'tt_price_list_mitrakeluarga_price_wizard_pcr_rel','timeslot_pcr_wizard_id', 'price_list_id', 'PCR')

    srbd_price_ids = fields.Many2many('tt.price.list.mitrakeluarga', 'tt_price_list_mitrakeluarga_price_wizard_srbd_rel','timeslot_srbd_wizard_id', 'price_list_id', 'SRBD')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)


    single_supplement = fields.Monetary('Single Supplement', default=SINGLE_SUPPLEMENT, required=True)
    overtime_surcharge = fields.Monetary('Overtime Surcharge', default=OVERTIME_SURCHARGE, required=True)
    cito_surcharge = fields.Monetary('Cito Surcharge', default=CITO_SURCHARGE, required=True)

    agent_id = fields.Many2one('tt.agent', 'Agent')
    default_data_id = fields.Many2one('tt.timeslot.mitrakeluarga.default', 'Default Data')

    # @api.model
    # def create(self, vals_list):
    #     new_rec = super(CreateTimeslotphcWizard, self).create(vals_list)
    #     if new_rec.default_data_id:
    #         new_rec.commission_antigen = new_rec.default_data_id.commission_antigen
    #         new_rec.commission_pcr = new_rec.default_data_id.commission_pcr
    #         new_rec.commission_pcr_priority = new_rec.default_data_id.commission_pcr_priority
    #         new_rec.commission_pcr_express = new_rec.default_data_id.commission_pcr_express
    #         new_rec.commission_srbd = new_rec.default_data_id.commission_srbd
    #         new_rec.base_price_antigen = new_rec.default_data_id.base_price_antigen
    #         new_rec.base_price_pcr = new_rec.default_data_id.base_price_pcr
    #         new_rec.base_price_pcr_dt = new_rec.default_data_id.base_price_pcr_dt
    #         new_rec.base_price_pcr_priority = new_rec.default_data_id.base_price_pcr_priority
    #         new_rec.base_price_pcr_express = new_rec.default_data_id.base_price_pcr_express
    #         new_rec.base_price_srbd = new_rec.default_data_id.base_price_srbd
    #         new_rec.single_supplement = new_rec.default_data_id.single_supplement
    #         new_rec.overtime_surcharge = new_rec.default_data_id.overtime_surcharge
    #         new_rec.admin_fee_antigen_drivethru = new_rec.default_data_id.admin_fee_antigen_drivethru
    #     return new_rec

    @api.onchange('default_data_id')
    @api.depends('default_data_id')
    def _onchange_default_data_timeslot(self):
        self.antigen_price_ids = self.default_data_id.antigen_price_ids
        self.pcr_price_ids = self.default_data_id.pcr_price_ids
        self.srbd_price_ids = self.default_data_id.srbd_price_ids
        self.single_supplement = self.default_data_id.single_supplement
        self.overtime_surcharge = self.default_data_id.overtime_surcharge
        self.cito_surcharge = self.default_data_id.cito_surcharge

    @api.onchange('start_date')
    def _onchange_start_date(self):
        for rec in self:
            rec.end_date = rec.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                rec.end_date = rec.start_date

    def _get_area_id_domain(self):
        return [('provider_type_id','=',self.env.ref('tt_reservation_mitrakeluarga.tt_provider_type_mitrakeluarga').id)]

    area_id = fields.Many2one('tt.destinations', 'Area', domain=_get_area_id_domain, required=True)

    def generate_timeslot(self, from_cron=False): #HOMECARE
        date_delta = self.end_date - self.start_date
        date_delta = date_delta.days+1
        create_values = []
        timelist = self.time_string.split(',')

        #price list
        antigen_list = False
        pcr_list = False
        srbd_list = False
        if from_cron == True:

            default_data = self.env.ref('tt_reservation_mitrakeluarga.tt_timeslot_mitrakeluarga_default_data_homecare_sub')
            antigen_list = [(6, 0, [x.id for x in default_data.antigen_price_ids])]
            pcr_list = [(6, 0, [x.id for x in default_data.pcr_price_ids])]
            srbd_list = [(6, 0, [x.id for x in default_data.srbd_price_ids])]
            single_supplement = default_data.single_supplement
            overtime_surcharge = default_data.overtime_surcharge
            cito_surcharge = default_data.cito_surcharge
        else:
            if self.antigen_price_ids:
                antigen_list = [(6, 0, [x.id for x in self.antigen_price_ids])]
            if self.pcr_price_ids:
                pcr_list = [(6, 0, [x.id for x in self.pcr_price_ids])]
            if self.srbd_price_ids:
                srbd_list = [(6, 0, [x.id for x in self.srbd_price_ids])]
            single_supplement = self.single_supplement
            overtime_surcharge = self.overtime_surcharge
            cito_surcharge = self.cito_surcharge
        ##convert to timezone 0
        time_objs = []
        for idx, time_str in enumerate(timelist):
            time_objs.append((datetime.strptime(time_str,'%H:%M') - timedelta(hours=7)).time())

        db = self.env['tt.timeslot.mitrakeluarga'].search([('destination_id','=',self.area_id.id), ('dateslot','>=',self.start_date), ('dateslot','<=',self.end_date), ('timeslot_type','=',self.timeslot_type), ('agent_id','=',self.agent_id.id if self.agent_id else False)])
        db_list = [str(data.datetimeslot) for data in db]
        for this_date_counter in range(date_delta):
            for idx, this_time in enumerate(time_objs):
                this_date = self.start_date + timedelta(days=this_date_counter)
                datetimeslot = datetime.strptime('%s %s' % (str(this_date),this_time),'%Y-%m-%d %H:%M:%S')
                max_book_datetime = datetimeslot.replace(hour=8, minute=0, second=0, microsecond=0)
                if str(datetimeslot) not in db_list:
                    create_values.append({
                        'dateslot': this_date,
                        'datetimeslot': datetimeslot,
                        'destination_id': self.area_id.id,
                        'total_timeslot': self.total_timeslot,
                        'currency_id': self.currency_id.id,
                        'timeslot_type': self.timeslot_type,
                        'antigen_price_ids': antigen_list,
                        'pcr_price_ids': pcr_list,
                        'srbd_price_ids': srbd_list,
                        'max_book_datetime': max_book_datetime,
                        'single_supplement': single_supplement,
                        'overtime_surcharge': overtime_surcharge,
                        'cito_surcharge': cito_surcharge,
                        'agent_id': self.agent_id.id if self.agent_id else False,
                    })

        self.env['tt.timeslot.mitrakeluarga'].create(create_values)

    def generate_drivethru_timeslot(self, date, max_timeslot=3, adult_timeslot=420, pcr_timeslot=195):
        destination = self.env['tt.destinations'].search([('code','=','SUB'),('provider_type_id','=',self.env.ref('tt_reservation_mitrakeluarga.tt_provider_type_mitrakeluarga').id)])
        datetimeslot = datetime.strptime('%s %s' % (str(date), '02:09:09'), '%Y-%m-%d %H:%M:%S')
        datetimeslot_end = datetime.strptime('%s %s' % (str(date), '08:09:09'), '%Y-%m-%d %H:%M:%S')
        for rec in destination:
            db = self.env['tt.timeslot.mitrakeluarga'].search(
                [('destination_id', '=', rec.id), ('dateslot', '=', date),
                 ('timeslot_type', '=', 'drive_thru')])
            if not db:
                default_data_obj = self.env['tt.timeslot.mitrakeluarga.default'].search([('id','=', self.env.ref('tt_reservation_mitrakeluarga.tt_timeslot_mitrakeluarga_default_data_drivethru_sub').id)], limit=1)

                if datetimeslot.strftime('%A') != 'Sunday': # DRIVE THRU TIDAK ADA HARI MINGGU
                    antigen_list = [(6, 0, [x.id for x in default_data_obj.antigen_price_ids])]
                    pcr_list = [(6, 0, [x.id for x in default_data_obj.pcr_price_ids])]
                    srbd_list = [(6, 0, [x.id for x in default_data_obj.srbd_price_ids])]
                    single_supplement = default_data_obj.single_supplement
                    overtime_surcharge = default_data_obj.overtime_surcharge
                    cito_surcharge = default_data_obj.cito_surcharge
                    max_book_datetime = datetimeslot.replace(hour=8, minute=30, second=0, microsecond=0)
                    self.env['tt.timeslot.mitrakeluarga'].create({
                        'dateslot': date,
                        'datetimeslot': datetimeslot,
                        'destination_id': rec.id,
                        'max_book_datetime': max_book_datetime,
                        'total_timeslot': pcr_timeslot,
                        'currency_id': self.env.user.company_id.currency_id.id,
                        'timeslot_type': 'drive_thru',
                        'antigen_price_ids': antigen_list,
                        'pcr_price_ids': pcr_list,
                        'srbd_price_ids': srbd_list,
                        'single_supplement': single_supplement,
                        'overtime_surcharge': overtime_surcharge,
                        'cito_surcharge': cito_surcharge,
                        'agent_id': False,
                    })