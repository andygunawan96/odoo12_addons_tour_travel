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
SINGLE_SUPPLEMENT = 0 ## 1 orang
OVERTIME_SURCHARGE = 0 ## lebih dari 18.00 /pax
CITO_SURCHARGE = 0## Urgent cito surcharge range 2-5jam stlh jam book

class TtTimeslotLabPintar(models.Model):
    _name = 'tt.timeslot.labpintar'
    _description = 'Rodex Model Timeslot Lab Pintar'
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

    booking_ids = fields.Many2many('tt.reservation.labpintar','tt_reservation_labpintar_timeslot_rel', 'timeslot_id', 'booking_id', 'Selected on By Customer Booking(s)')

    antigen_price_ids = fields.Many2many('tt.price.list.labpintar','tt_price_list_labpintar_price_antigen_rel','timeslot_antigen_id', 'price_list_id', 'Antigen')

    pcr_price_ids = fields.Many2many('tt.price.list.labpintar','tt_price_list_labpintar_price_pcr_rel','timeslot_pcr_id', 'price_list_id', 'PCR')

    pcr_express_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_pcr_express_rel',
                                     'timeslot_pcr_express_id', 'price_list_id', 'PCR Express')

    pcr_priority_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_pcr_priority_rel',
                                     'timeslot_pcr_priority_id', 'price_list_id', 'PCR Priority')

    srbd_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_srbd_rel',
                                     'timeslot_srbd_id', 'price_list_id', 'SRBD')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    booking_used_ids = fields.One2many('tt.reservation.labpintar','picked_timeslot_id', 'Confirmed to Customer Booking(s)')

    single_supplement = fields.Monetary('Single Supplement')
    overtime_surcharge = fields.Monetary('Overtime Surcharge')
    cito_surcharge = fields.Monetary('Cito Surcharge')

    total_timeslot = fields.Integer('Max Timeslot', required=True, default=5)

    active = fields.Boolean('Active', default='True')

    agent_id = fields.Many2one('tt.agent', 'Agent')

    @api.depends('datetimeslot')
    def _compute_timeslot_display_name(self):
        for rec in self:
            rec.timeslot_display_name = "%s %s" % (str(rec.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')))[:19], rec.destination_id.name)

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.timeslot.labpintar')
        return super(TtTimeslotLabPintar, self).create(vals_list)

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
        if '09:00' < str(current_wib_datetime.time())[:5] < '18:00': # MAX BELI JAM 6 SORE
            dom = ['|',('agent_id','=',False),('agent_id', '=', context['co_agent_id']),('datetimeslot', '>', datetime.now(pytz.utc) + timedelta(hours=6))]
        else:
            min_datetime = current_datetime.replace(hour=8,minute=0, second=0, microsecond=0) #KALAU DILUAR JAM OPERATIONAL JAM 3 BARU BOLEH BELI
            if current_datetime > min_datetime:
                min_datetime = min_datetime + timedelta(days=1)
            dom = ['|',('agent_id','=',False),('agent_id', '=', context['co_agent_id']),('datetimeslot', '>', min_datetime)]

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
        print(json.dumps(timeslot_dict))
        return ERR.get_no_error(timeslot_dict)

    def get_availability(self):
        return self.used_count < self.total_timeslot

    def get_datetimeslot_str(self):
        if self.datetimeslot:
            return self.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')).strftime('%d %B %Y %H:%M')
        else:
            return 'Date/Time is not specified.'

    def get_config_cron(self):
        result = self.env['tt.labpintar.api.con'].get_config_cron()
        return result

    def to_dict(self):

        res = {
            "datetimeslot": self.datetimeslot.strftime('%Y-%m-%d %H:%M'),
            "area": self.destination_id.city,
        }

        return res

class TtTimeslotlabpintardefault(models.Model):
    _name = 'tt.timeslot.labpintar.default'
    _description = 'Rodex Model Timeslot Lab Pintar Default'
    _order = 'sequence'

    name = fields.Char("Name", required=True)
    sequence = fields.Integer("Sequence",default=200)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    antigen_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_antigen_default_rel',
                                         'timeslot_antigen_id', 'price_list_id', 'Antigen')

    pcr_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_pcr_default_rel',
                                     'timeslot_pcr_id', 'price_list_id', 'PCR')

    pcr_express_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_pcr_express_default_rel',
                                     'timeslot_pcr_express_id', 'price_list_id', 'PCR Express')

    pcr_priority_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_pcr_priority_default_rel',
                                     'timeslot_pcr_priority_id', 'price_list_id', 'PCR Priority')

    srbd_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_srbd_default_rel',
                                     'timeslot_srbd_id', 'price_list_id', 'SRBD')


    single_supplement = fields.Monetary('Single Supplement', default=SINGLE_SUPPLEMENT, required=True)
    overtime_surcharge = fields.Monetary('Overtime Surcharge', default=OVERTIME_SURCHARGE, required=True)

    cito_surcharge = fields.Monetary('Cito Surcharge', default=CITO_SURCHARGE, required=True)
    time_string = fields.Text('Time String', default='08:00,09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,18:00', required=True)
