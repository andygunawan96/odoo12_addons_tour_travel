import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)

COMMISSION_PER_PAX = 22000 ## komisi agent /pax
BASE_PRICE_PER_PAX = 150000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR = 750000 ## harga 1 /pax
SINGLE_SUPPLEMENT = 25000 ## 1 orang
OVERTIME_SURCHARGE = 50000 ## lebih dari 18.00 /pax
CITO_SURCHARGE = 25000## Urgent cito surcharge range 2-5jam stlh jam book

class CreateTimeslotPeriksainWizard(models.TransientModel):
    _name = "create.timeslot.periksain.wizard"
    _description = 'Periksain Create Timeslot Wizard'

    start_date = fields.Date('Start Date',required=True, default=fields.Date.context_today)
    end_date = fields.Date('End Date',required=True, default=fields.Date.context_today)
    time_string = fields.Text('Time',default='08:00,09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,18:00,19:00,20:00,21:00')

    id_time_vendor = fields.Text('ID Time Vendor', default='')
    id_jenis_tindakan_vendor = fields.Text('ID Jenis Tindakan Vendor', default='')

    timeslot_type = fields.Selection([('home_care', 'Home Care'), ('group_booking', 'Group Booking')], 'Timeslot Type', default='home_care',
                                     required=True)
    total_timeslot = fields.Integer('Total Timeslot', default=5, required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    commission_antigen = fields.Monetary('Commission per PAX Antigen', default=COMMISSION_PER_PAX,
                                         required=True)
    commission_pcr = fields.Monetary('Commission per PAX PCR', default=COMMISSION_PER_PAX, required=True)

    base_price_antigen = fields.Monetary('Base Price per PAX Antigen', default=BASE_PRICE_PER_PAX,
                                         required=True)
    base_price_pcr = fields.Monetary('Base Price per PAX PCR', default=BASE_PRICE_PER_PAX_PCR, required=True)

    single_supplement = fields.Monetary('Single Supplement', default=SINGLE_SUPPLEMENT, required=True)
    overtime_surcharge = fields.Monetary('Overtime Surcharge', default=OVERTIME_SURCHARGE, required=True)
    cito_surcharge = fields.Monetary('Cito Surcharge', default=CITO_SURCHARGE, required=True)

    agent_id = fields.Many2one('tt.agent', 'Agent')

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
        return [('provider_type_id','=',self.env.ref('tt_reservation_periksain.tt_provider_type_periksain').id)]

    area_id = fields.Many2one('tt.destinations', 'Area', domain=_get_area_id_domain, required=True)

    def generate_timeslot(self):
        date_delta = self.end_date - self.start_date
        date_delta = date_delta.days+1
        create_values = []
        timelist = self.time_string.split(',')
        id_timelist_periksain = self.id_time_vendor.split(',')
        ##convert to timezone 0
        time_objs = []
        time_objs_id_periksain = []
        for idx, time_str in enumerate(timelist):
            time_objs.append((datetime.strptime(time_str,'%H:%M') - timedelta(hours=7)).time())
            time_objs_id_periksain.append(id_timelist_periksain[idx] if len(id_timelist_periksain) > idx else id_timelist_periksain[0])

        db = self.env['tt.timeslot.periksain'].search([('destination_id','=',self.area_id.id), ('dateslot','>=',self.start_date), ('dateslot','<=',self.end_date), ('timeslot_type','=',self.timeslot_type), ('agent_id','=',self.agent_id.id if self.agent_id else False)])
        db_list = [str(data.datetimeslot) for data in db]
        for this_date_counter in range(date_delta):
            for idx, this_time in enumerate(time_objs):
                this_date = self.start_date + timedelta(days=this_date_counter)
                datetimeslot = datetime.strptime('%s %s' % (str(this_date),this_time),'%Y-%m-%d %H:%M:%S')
                if str(datetimeslot) not in db_list:
                    create_values.append({
                        'dateslot': this_date,
                        'datetimeslot': datetimeslot,
                        'destination_id': self.area_id.id,
                        'time_slot': self.total_timeslot,
                        'currency_id': self.currency_id.id,
                        'timeslot_type': self.timeslot_type,
                        'commission_antigen': self.commission_antigen,
                        'commission_pcr': self.commission_pcr,
                        'base_price_antigen': self.base_price_antigen,
                        'base_price_pcr': self.base_price_pcr,
                        'single_supplement': self.single_supplement,
                        'overtime_surcharge': self.overtime_surcharge,
                        'cito_surcharge': self.overtime_surcharge,
                        'agent_id': self.agent_id.id if self.agent_id else False,
                        'id_kota_vendor': self.area_id.icao.split('~')[0],
                        'id_time_vendor': time_objs_id_periksain[idx],
                        'tindakan_pemeriksaan_vendor': self.area_id.icao.split('~')[1]
                    })

        self.env['tt.timeslot.periksain'].create(create_values)