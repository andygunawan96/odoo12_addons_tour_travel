from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta

_logger = logging.getLogger(__name__)


class CreateTimeslotPeriksainWizard(models.TransientModel):
    _name = "create.timeslot.periksain.wizard"
    _description = 'Periksain Create Timeslot Wizard'

    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    time_string = fields.Text('Time',default='08:00,08:50,09:40,10:30,11:20,12:10,13:00,13:50,14:40,15:30,16:20,17:10,18:00,18:50,19:40,20:30')
    area = fields.Many2one('Area',domain="[('provider_type_id','=',ref('tt_provider_type_periksain')]")

    def generate_timeslot(self):
        date_delta = self.end_date - self.start_date + timedelta(days=1)
        write_values = []
        timelist = self.time_string.split(',')
        for date in date_delta:
            for time in timelist:
                write_values.append((0,0,{
                    ''
                }))
