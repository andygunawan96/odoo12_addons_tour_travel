import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)


class CreateTimeslotphcWizard(models.TransientModel):
    _name = "create.timeslot.phc.wizard"
    _description = 'phc Create Timeslot Wizard'

    start_date = fields.Date('Start Date',required=True, default=fields.Date.today())
    end_date = fields.Date('End Date',required=True, default=fields.Date.today())
    time_string = fields.Text('Time',default='08:00,09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00')

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

        db = self.env['tt.timeslot.phc'].search([('destination_id','=',self.area_id.id), ('dateslot','>=',self.start_date), ('dateslot','<=',self.end_date)])
        db_list = [str(data.datetimeslot) for data in db]
        for this_date_counter in range(date_delta):
            for this_time in time_objs:
                this_date = self.start_date + timedelta(days=this_date_counter)
                datetimeslot = datetime.strptime('%s %s' % (str(this_date),this_time),'%Y-%m-%d %H:%M:%S')
                if str(datetimeslot) not in db_list:
                    create_values.append({
                        'dateslot': this_date,
                        'datetimeslot': datetimeslot,
                        'destination_id': self.area_id.id
                    })

        self.env['tt.timeslot.phc'].create(create_values)
