import pytz

from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime,date, timedelta
import base64
import json


_logger = logging.getLogger(__name__)

MAX_PER_SLOT = 5

class TtTimeslotPeriksain(models.Model):
    _name = 'tt.timeslot.periksain'
    _description = 'Rodex Model Timeslot Periksain'
    _order = 'datetimeslot'

    seq_id = fields.Char('Sequence ID')

    dateslot = fields.Date('dateslot')

    datetimeslot = fields.Datetime('DateTime Slot')

    destination_id = fields.Many2one('tt.destination','Area')

    used_count = fields.Integer('Used Counter',compute="_compute_used_counter",store=True)

    booking_ids = fields.Many2many('tt.reservation.periksain','tt_reservation_periksain_timeslot_rel', 'timeslot_id', 'booking_id', 'Booking(s)')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.timeslot.periksain')
        return super(TtTimeslotPeriksain, self).create(vals_list)

    @api.depends('booking_ids')
    def _compute_used_counter(self):
        for rec in self:
            rec.used_count = len(rec.booking_ids)

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

    def get_available_timeslot_api(self):
        timeslots = self.search([('datetimeslot','>',datetime.now(pytz.utc))])
        max_date = date.today()
        date()
        timeslot_dict = {}
        for rec in timeslots:
            if rec.dateslot > max_date:
                max_date = rec.dateslot
            if rec.destination_id.name not in timeslot_dict:
                timeslot_dict[rec.destination_id.name] = {}
            timeslot_dict[rec.rec.destination_id.name][str(rec.dateslot)].append({
                'time': str(rec.datetimeslot)[11:16],
                'seq_id': rec.seq_id,
                'availability': rec.get_availability()
            })
        res = {
            'max_date': max_date,
            'timeslots': timeslot_dict,
        }
        return ERR.get_no_error(res)

    def get_availability(self):
        return self.used_count < MAX_PER_SLOT