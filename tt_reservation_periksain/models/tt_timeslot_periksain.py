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
    _description = 'Orbis Model Timeslot Periksain'
    _order = 'datetimeslot'
    _rec_name = 'timeslot_display_name'

    seq_id = fields.Char('Sequence ID',readonly=True)

    dateslot = fields.Date('Dateslot',readonly=True)

    datetimeslot = fields.Datetime('DateTime Slot')
    timeslot_display_name = fields.Char('Display Name', compute="_compute_timeslot_display_name")
    timeslot_type = fields.Selection(
        [('home_care', 'Home Care'), ('group_booking', 'Group Booking')], 'Timeslot Type')

    destination_id = fields.Many2one('tt.destinations','Area')

    selected_count = fields.Integer('Selected Counter',compute="_compute_selected_counter",store=True)

    used_count = fields.Integer('Used Counter',compute="_compute_used_counter",store=True)

    booking_ids = fields.Many2many('tt.reservation.periksain','tt_reservation_periksain_timeslot_rel', 'timeslot_id', 'booking_id', 'Selected on By Customer Booking(s)')

    booking_used_ids = fields.One2many('tt.reservation.periksain','picked_timeslot_id', 'Confirmed to Customer Booking(s)')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    commission_antigen = fields.Monetary('Commission per PAX Antigen')
    commission_pcr = fields.Monetary('Commission per PAX PCR')

    base_price_antigen = fields.Monetary('Base Price per PAX Antigen')
    base_price_pcr = fields.Monetary('Base Price per PAX PCR')

    single_supplement = fields.Monetary('Single Supplement')
    overtime_surcharge = fields.Monetary('Overtime Surcharge')
    cito_surcharge = fields.Monetary('Cito Surcharge')

    total_timeslot = fields.Integer('Max Timeslot', required=True, default=5)

    active = fields.Boolean('Active', default='True')

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent')

    id_kota_vendor = fields.Char('Kota ID Vendor')
    id_time_vendor = fields.Char('Timeslot Periksain ID Vendor')
    tindakan_pemeriksaan_vendor = fields.Char('Tindakan Pemeriksaan Vendor')

    @api.depends('datetimeslot')
    def _compute_timeslot_display_name(self):
        for rec in self:
            rec.timeslot_display_name = "%s %s" % (str(rec.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')))[:19], rec.destination_id.name)

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.timeslot.periksain')
        return super(TtTimeslotPeriksain, self).create(vals_list)

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

    def get_available_timeslot_api(self, context):
        current_wib_datetime = datetime.now(pytz.timezone('Asia/Jakarta'))
        current_datetime = current_wib_datetime.astimezone(pytz.utc)
        malang_id = self.env.ref('tt_reservation_periksain.tt_destination_periksain_mlg').id
        if '08:00' < str(current_wib_datetime.time())[:5] < '17:00':
            dom = ['|',('agent_id','=',False),('agent_id', '=', context['co_agent_id']),('datetimeslot', '>', datetime.now(pytz.utc) + timedelta(hours=3))]
        else:
            min_datetime = current_datetime.replace(hour=7,minute=0, second=0, microsecond=0)
            if current_datetime > min_datetime:
                min_datetime = min_datetime + timedelta(days=1)
            dom = ['|',('agent_id','=',False),('agent_id', '=', context['co_agent_id']),('datetimeslot', '>', min_datetime),
                   ('destination_id', '!=', malang_id)]

        timeslots = self.search(dom)
        # max_date = date.today()
        timeslot_dict = {}
        for rec in timeslots:
            #skip malang utk hari H
            if current_datetime.date() == rec.dateslot and rec.destination_id.id == malang_id:
                continue

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
        return self.used_count < self.total_timeslot

    def get_datetimeslot_str(self):
        if self.datetimeslot:
            return self.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')).strftime('%d %B %Y %H:%M')
        else:
            return 'Date/Time is not specified.'

    def get_config_cron(self):
        ## tambah context
        ## TIDAK DIPAKAI JADI TIDAK DI UPDATE
        result = self.env['tt.periksain.api.con'].get_config_cron()
        return result

    def to_dict(self):

        res = {
            "datetimeslot": self.datetimeslot.strftime('%Y-%m-%d %H:%M'),
            "area": self.destination_id.city,
            "id_kota_vendor": self.id_kota_vendor,
            "id_time_vendor": self.id_time_vendor,
            "tindakan_pemeriksaan_vendor": json.loads(self.tindakan_pemeriksaan_vendor) if self.tindakan_pemeriksaan_vendor else False
        }

        return res