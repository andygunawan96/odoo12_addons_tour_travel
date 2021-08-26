from odoo import api, fields, models, _
from datetime import timedelta,datetime
import logging

_logger = logging.getLogger(__name__)

class CreateTimeslotphcWizard(models.TransientModel):
    _name = "create.timeslot.phc.wizard"
    _description = 'phc Create Timeslot Wizard'

    start_date = fields.Date('Start Date',required=True, default=fields.Date.context_today)
    end_date = fields.Date('End Date',required=True, default=fields.Date.context_today)
    time_string = fields.Text('Time',default='07:00-09:00-surabaya_timur,09:00-11:00-surabaya_utara,11:00-13:00-surabaya_barat,13:00-15:00-surabaya_selatan,15:00-18:00-surabaya_pusat')

    timeslot_type = fields.Selection([('home_care', 'Home Care'), ('group_booking', 'Group Booking')], 'Timeslot Type',
                                     default='home_care', required=True)

    total_timeslot = fields.Integer('Total Timeslot',default=5, required=True)
    total_adult_timeslot = fields.Integer('Total Adult Timeslot',default=420, required=True)
    total_pcr_timeslot = fields.Integer('Total PCR Timeslot',default=195, required=True)

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    commission_antigen = fields.Monetary('Commission per PAX Antigen')
    commission_pcr = fields.Monetary('Commission per PAX PCR')
    commission_pcr_priority = fields.Monetary('Commission per PAX PCR Priority')
    commission_pcr_express = fields.Monetary('Commission per PAX PCR Express')

    base_price_antigen = fields.Monetary('Base Price per PAX Antigen')
    base_price_pcr = fields.Monetary('Base Price per PAX PCR')
    base_price_pcr_priority = fields.Monetary('Base Price per PAX PCR Priority')
    base_price_pcr_express = fields.Monetary('Base Price per PAX PCR Express')

    single_supplement = fields.Monetary('Single Supplement')
    overtime_surcharge = fields.Monetary('Overtime Surcharge')

    agent_id = fields.Many2one('tt.agent', 'Agent')
    default_data_id = fields.Many2one('tt.timeslot.phc.default', 'Default Data')

    @api.model
    def create(self, vals_list):
        new_rec = super(CreateTimeslotphcWizard, self).create(vals_list)
        if new_rec.default_data_id:
            new_rec.commission_antigen = new_rec.default_data_id.commission_antigen
            new_rec.commission_pcr = new_rec.default_data_id.commission_pcr
            new_rec.commission_pcr_priority = new_rec.default_data_id.commission_pcr_priority
            new_rec.commission_pcr_express = new_rec.default_data_id.commission_pcr_express
            new_rec.base_price_antigen = new_rec.default_data_id.base_price_antigen
            new_rec.base_price_pcr = new_rec.default_data_id.base_price_pcr
            new_rec.base_price_pcr_dt = new_rec.default_data_id.base_price_pcr_dt
            new_rec.base_price_pcr_priority = new_rec.default_data_id.base_price_pcr_priority
            new_rec.base_price_pcr_express = new_rec.default_data_id.base_price_pcr_express
            new_rec.single_supplement = new_rec.default_data_id.single_supplement
            new_rec.overtime_surcharge = new_rec.default_data_id.overtime_surcharge
        return new_rec

    @api.onchange('default_data_id')
    @api.depends('default_data_id')
    def _onchange_default_data_timeslot(self):
        self.commission_antigen = self.default_data_id.commission_antigen
        self.commission_pcr = self.default_data_id.commission_pcr
        self.commission_pcr_priority = self.default_data_id.commission_pcr_priority
        self.commission_pcr_express = self.default_data_id.commission_pcr_express
        self.base_price_antigen = self.default_data_id.base_price_antigen
        self.base_price_pcr = self.default_data_id.base_price_pcr
        self.base_price_pcr_dt = self.default_data_id.base_price_pcr_dt
        self.base_price_pcr_priority = self.default_data_id.base_price_pcr_priority
        self.base_price_pcr_express = self.default_data_id.base_price_pcr_express
        self.single_supplement = self.default_data_id.single_supplement
        self.overtime_surcharge = self.default_data_id.overtime_surcharge

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

    @api.onchange('')
    def generate_timeslot(self):
        date_delta = self.end_date - self.start_date
        date_delta = date_delta.days+1
        create_values = []
        timelist = self.time_string.split(',')

        ##convert to timezone 0
        time_objs = []
        for time_str in timelist:
            time_str_list = time_str.split('-')

            time_objs.append([(datetime.strptime(time_str_list[0],'%H:%M') - timedelta(hours=7)).time(),
                             (datetime.strptime(time_str_list[1],'%H:%M') - timedelta(hours=7)).time(),
                             time_str_list[2]])

        db = self.env['tt.timeslot.phc'].search([('destination_id','=',self.area_id.id), ('dateslot','>=',self.start_date), ('dateslot','<=',self.end_date), ('timeslot_type','=',self.timeslot_type), ('agent_id','=',self.agent_id.id if self.agent_id else False)])
        db_list = [str(data.datetimeslot) for data in db]
        for this_date_counter in range(date_delta):
            for this_time in time_objs:
                this_date = self.start_date + timedelta(days=this_date_counter)
                datetimeslot = datetime.strptime('%s %s' % (str(this_date),this_time[0]),'%Y-%m-%d %H:%M:%S')
                datetimeslot_end = datetime.strptime('%s %s' % (str(this_date),this_time[1]),'%Y-%m-%d %H:%M:%S')
                if str(datetimeslot) not in db_list:
                    create_values.append({
                        'dateslot': this_date,
                        'datetimeslot': datetimeslot,
                        'datetimeslot_end': datetimeslot_end,
                        'max_book_datetime': datetimeslot.replace(hour=9, minute=0, second=0, microsecond=0) - timedelta(days=1),
                        'destination_id': self.area_id.id,
                        'destination_area': this_time[2],
                        'total_timeslot': self.total_timeslot,
                        'total_adult_timeslot': self.total_adult_timeslot,
                        'total_pcr_timeslot': self.total_pcr_timeslot,
                        'currency_id': self.currency_id.id,
                        'timeslot_type': self.timeslot_type,
                        'commission_antigen': self.commission_antigen,
                        'commission_pcr': self.commission_pcr,
                        'commission_pcr_priority': self.commission_pcr_priority,
                        'commission_pcr_express': self.commission_pcr_express,
                        'base_price_antigen': self.base_price_antigen,
                        'base_price_pcr': self.base_price_pcr,
                        'base_price_pcr_priority': self.base_price_pcr_priority,
                        'base_price_pcr_express': self.base_price_pcr_express,
                        'single_supplement': self.single_supplement,
                        'overtime_surcharge': self.overtime_surcharge,
                        'agent_id': self.agent_id.id if self.agent_id else False
                    })
        self.env['tt.timeslot.phc'].create(create_values)

    def generate_drivethru_timeslot(self, date, max_timeslot=5, adult_timeslot=420, pcr_timeslot=195):
        destination = self.env['tt.destinations'].search([('provider_type_id','=',self.env.ref('tt_reservation_phc.tt_provider_type_phc').id),('code','=','SUB')])
        datetimeslot = datetime.strptime('%s %s' % (str(date), '02:09:09'), '%Y-%m-%d %H:%M:%S')
        datetimeslot_end = datetime.strptime('%s %s' % (str(date), '08:09:09'), '%Y-%m-%d %H:%M:%S')
        db = self.env['tt.timeslot.phc'].search(
            [('destination_id', '=', destination.id), ('dateslot', '=', date),
             ('timeslot_type', '=', 'drive_thru')])
        if not db:
            default_data_obj = self.env['tt.timeslot.phc.default'].search([], limit=1)
            self.env['tt.timeslot.phc'].create({
                'dateslot': date,
                'datetimeslot': datetimeslot,
                'datetimeslot_end': datetimeslot_end,
                'max_book_datetime': datetimeslot.replace(hour=9,minute=0,second=0,microsecond=0),
                'destination_id': destination.id,
                'destination_area': 'surabaya_all',
                'total_timeslot': max_timeslot,
                'total_adult_timeslot': adult_timeslot,
                'total_pcr_timeslot': pcr_timeslot,
                'currency_id': self.env.user.company_id.currency_id.id,
                'timeslot_type': 'drive_thru',
                'commission_antigen': default_data_obj.commission_antigen,
                'commission_pcr': default_data_obj.commission_pcr_dt,
                'commission_pcr_priority': default_data_obj.commission_pcr_priority,
                'commission_pcr_express': default_data_obj.commission_pcr_express,
                'base_price_antigen': default_data_obj.base_price_antigen,
                'base_price_pcr': default_data_obj.base_price_pcr_dt,
                'base_price_pcr_priority': default_data_obj.base_price_pcr_priority,
                'base_price_pcr_express': default_data_obj.base_price_pcr_express,
                'single_supplement': default_data_obj.single_supplement,
                'overtime_surcharge': default_data_obj.overtime_surcharge,
                'agent_id': False
            })
