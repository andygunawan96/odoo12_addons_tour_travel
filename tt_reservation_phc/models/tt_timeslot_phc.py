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

class TtTimeslotphc(models.Model):
    _name = 'tt.timeslot.phc'
    _description = 'Rodex Model Timeslot phc'
    _order = 'datetimeslot,id'
    _rec_name = 'timeslot_display_name'

    seq_id = fields.Char('Sequence ID')

    dateslot = fields.Date('Dateslot')

    datetimeslot = fields.Datetime('DateTime Slot')
    timeslot_display_name = fields.Char('Display Name', compute="_compute_timeslot_display_name")
    timeslot_type = fields.Selection([('home_care', 'Home Care'), ('drive_thru', 'Drive Thru'), ('group_booking', 'Group Booking')], 'Timeslot Type')

    destination_id = fields.Many2one('tt.destinations','Area')

    selected_count = fields.Integer('Selected Counter',compute="_compute_selected_counter",store=True)

    used_count = fields.Integer('Used Counter',compute="_compute_used_counter",store=True)

    booking_ids = fields.Many2many('tt.reservation.phc','tt_reservation_phc_timeslot_rel', 'timeslot_id', 'booking_id', 'Selected on By Customer Booking(s)')

    booking_used_ids = fields.One2many('tt.reservation.phc','picked_timeslot_id', 'Confirmed to Customer Booking(s)')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    commission_antigen = fields.Monetary('Commission per PAX Antigen')
    commission_pcr = fields.Monetary('Commission per PAX PCR')

    base_price_antigen = fields.Monetary('Base Price per PAX Antigen')
    base_price_pcr = fields.Monetary('Base Price per PAX PCR')

    single_supplement = fields.Monetary('Single Supplement')
    overtime_surcharge = fields.Monetary('Overtime Surcharge')

    total_timeslot = fields.Integer('Max Timeslot', required=True, default=5)

    active = fields.Boolean('Active', default='True')

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

    @api.onchange('booking_ids')
    @api.depends('booking_ids')
    def _compute_selected_counter(self):
        for rec in self:
            rec.selected_count = len(rec.booking_ids.ids)

    @api.onchange('booking_used_ids')
    @api.depends('booking_used_ids')
    def _compute_used_counter(self):
        for rec in self:
            used_count = 0
            for rec2 in rec.booking_used_ids:
                if rec2.state in ['booked', 'issued']:
                    used_count += 1
            rec.used_count = used_count

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
        carrier_id = self.env['tt.transport.carrier'].search([('code','=',req['carrier_code'])],limit=1).id

        dom = ['|', ('agent_id', '=', False), ('agent_id', '=', context['co_agent_id'])]

        if carrier_id in [self.env.ref('tt_reservation_phc.tt_transport_carrier_phc_home_care_antigen').id,
                          self.env.ref('tt_reservation_phc.tt_transport_carrier_phc_home_care_pcr').id]:
            dom.append(('timeslot_type', 'in', ['home_care', 'group_booking']))
            if '06:00' < str(current_wib_datetime.time())[:5] < '14:00':
                dom.append(('datetimeslot', '>=', datetime.now(pytz.utc) + timedelta(hours=2)))
            else:
                min_datetime = current_datetime.replace(hour=1, minute=0, second=0, microsecond=0)
                if current_datetime > min_datetime:
                    min_datetime = min_datetime + timedelta(days=1)
                dom.append(('datetimeslot', '>=', min_datetime))
        else:
            dom.append(('timeslot_type', '=', 'drive_thru'))
            ## kalau kurang dari jam 16.00 di tambah timedelta 0 else di tambah 1 hari
            dom.append(('dateslot', '>=', datetime.today() if current_wib_datetime <= current_wib_datetime.replace(hour=16,minute=0,second=0,microsecond=0) else datetime.today() + timedelta(days=1)))
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
                'seq_id': rec.seq_id,
                'availability': rec.get_availability(),
                'group_booking': True if rec.agent_id else False
            })
        return ERR.get_no_error(timeslot_dict)

    def get_availability(self):
        if self.timeslot_type == 'drive_thru':
            return True
        return self.used_count < self.total_timeslot

    def get_datetimeslot_str(self):
        if self.datetimeslot:
            if self.timeslot_type != 'drive_thru':
                return self.datetimeslot.strftime('%d %B %Y %H:%M')
            else:
                return '%s (08:00 - 17:00 WIB)' % (self.datetimeslot.strftime('%d %B %Y'))
        else:
            return 'Date/Time is not specified.'
