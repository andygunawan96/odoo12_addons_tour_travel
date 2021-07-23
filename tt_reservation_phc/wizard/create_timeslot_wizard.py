import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)

COMMISSION_PER_PAX_ANTIGEN = 28000 ## komisi agent /pax
COMMISSION_PER_PAX_PCR_HC = 120000 ## komisi agent /pax
COMMISSION_PER_PAX_PCR_DT = 80000 ## komisi agent /pax
COMMISSION_PER_PAX_PCR_DT_EXPRESS = 500000 ## komisi agent /pax
BASE_PRICE_PER_PAX_ANTIGEN = 150000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR_HC = 850000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR_DT = 750000 ## harga 1 /pax
BASE_PRICE_PER_PAX_PCR_DT_EXPRESS = 4000000 ## harga 1 /pax
SINGLE_SUPPLEMENT = 25000 ## 1 orang
OVERTIME_SURCHARGE = 50000 ## lebih dari 18.00 /pax

class CreateTimeslotphcWizard(models.TransientModel):
    _name = "create.timeslot.phc.wizard"
    _description = 'phc Create Timeslot Wizard'

    start_date = fields.Date('Start Date',required=True, default=fields.Date.context_today)
    end_date = fields.Date('End Date',required=True, default=fields.Date.context_today)
    time_string = fields.Text('Time',default='08:00,09:00,10:00,11:00,13:00,14:00,15:00,16:00')

    timeslot_type = fields.Selection([('home_care', 'Home Care'), ('group_booking', 'Group Booking')], 'Timeslot Type',
                                     default='home_care', required=True)

    total_timeslot = fields.Integer('Total Timeslot',default=5, required=True)
    total_adult_timeslot = fields.Integer('Total Adult Timeslot',default=420, required=True)
    total_pcr_timeslot = fields.Integer('Total PCR Timeslot',default=195, required=True)

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    commission_antigen = fields.Monetary('Commission per PAX Antigen', default=COMMISSION_PER_PAX_ANTIGEN, required=True)
    commission_pcr = fields.Monetary('Commission per PAX PCR', default=COMMISSION_PER_PAX_PCR_HC, required=True)
    commission_pcr_express = fields.Monetary('Commission per PAX PCR Express', default=COMMISSION_PER_PAX_PCR_DT_EXPRESS, required=True)

    base_price_antigen = fields.Monetary('Base Price per PAX Antigen', default=BASE_PRICE_PER_PAX_ANTIGEN, required=True)
    base_price_pcr = fields.Monetary('Base Price per PAX PCR', default=BASE_PRICE_PER_PAX_PCR_HC, required=True)
    base_price_pcr_express = fields.Monetary('Base Price per PAX PCR Express', default=BASE_PRICE_PER_PAX_PCR_DT_EXPRESS, required=True)

    single_supplement = fields.Monetary('Single Supplement', default=SINGLE_SUPPLEMENT, required=True)
    overtime_surcharge = fields.Monetary('Overtime Surcharge', default=OVERTIME_SURCHARGE, required=True)

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
        return [('provider_type_id','=',self.env.ref('tt_reservation_phc.tt_provider_type_phc').id)]

    area_id = fields.Many2one('tt.destinations', 'Area', domain=_get_area_id_domain, required=True)

    def generate_timeslot(self):
        date_delta = self.end_date - self.start_date
        date_delta = date_delta.days+1
        create_values = []
        timelist = self.time_string.split(',')

        ##convert to timezone 0
        time_objs = []
        for time_str in timelist:
            time_objs.append((datetime.strptime(time_str,'%H:%M') - timedelta(hours=7)).time())

        db = self.env['tt.timeslot.phc'].search([('destination_id','=',self.area_id.id), ('dateslot','>=',self.start_date), ('dateslot','<=',self.end_date), ('timeslot_type','=',self.timeslot_type), ('agent_id','=',self.agent_id.id if self.agent_id else False)])
        db_list = [str(data.datetimeslot) for data in db]
        for this_date_counter in range(date_delta):
            for this_time in time_objs:
                this_date = self.start_date + timedelta(days=this_date_counter)
                datetimeslot = datetime.strptime('%s %s' % (str(this_date),this_time),'%Y-%m-%d %H:%M:%S')
                if str(datetimeslot) not in db_list:
                    create_values.append({
                        'dateslot': this_date,
                        'datetimeslot': datetimeslot,
                        'max_book_datetime': datetimeslot.replace(hour=9, minute=0, second=0, microsecond=0),
                        'destination_id': self.area_id.id,
                        'total_timeslot': self.total_timeslot,
                        'total_adult_timeslot': self.total_adult_timeslot,
                        'total_pcr_timeslot': self.total_pcr_timeslot,
                        'currency_id': self.currency_id.id,
                        'timeslot_type': self.timeslot_type,
                        'commission_antigen': self.commission_antigen,
                        'commission_pcr': self.commission_pcr,
                        'base_price_antigen': self.base_price_antigen,
                        'base_price_pcr': self.base_price_pcr,
                        'single_supplement': self.single_supplement,
                        'overtime_surcharge': self.overtime_surcharge,
                        'agent_id': self.agent_id.id if self.agent_id else False
                    })
        self.env['tt.timeslot.phc'].create(create_values)

    def generate_drivethru_timeslot(self, date, max_timeslot=5, adult_timeslot=420, pcr_timeslot=195):
        destination = self.env['tt.destinations'].search([('provider_type_id','=',self.env.ref('tt_reservation_phc.tt_provider_type_phc').id),('code','=','SUB')])
        datetimeslot = datetime.strptime('%s %s' % (str(date), '02:09:09'), '%Y-%m-%d %H:%M:%S')
        db = self.env['tt.timeslot.phc'].search(
            [('destination_id', '=', destination.id), ('dateslot', '=', date),
             ('timeslot_type', '=', 'drive_thru')])
        if not db:
            self.env['tt.timeslot.phc'].create({
                'dateslot': date,
                'datetimeslot': datetimeslot,
                'max_book_datetime': datetimeslot.replace(hour=9,minute=0,second=0,microsecond=0),
                'destination_id': destination.id,
                'total_timeslot': max_timeslot,
                'total_adult_timeslot': adult_timeslot,
                'total_pcr_timeslot': pcr_timeslot,
                'currency_id': self.env.user.company_id.currency_id.id,
                'timeslot_type': 'drive_thru',
                'commission_antigen': COMMISSION_PER_PAX_ANTIGEN,
                'commission_pcr': COMMISSION_PER_PAX_PCR_DT,
                'commission_pcr_express': COMMISSION_PER_PAX_PCR_DT_EXPRESS,
                'base_price_antigen': BASE_PRICE_PER_PAX_ANTIGEN,
                'base_price_pcr': BASE_PRICE_PER_PAX_PCR_DT,
                'base_price_pcr_express': BASE_PRICE_PER_PAX_PCR_DT_EXPRESS,
                'single_supplement': SINGLE_SUPPLEMENT,
                'overtime_surcharge': OVERTIME_SURCHARGE,
                'agent_id': False
            })
