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

class CreateTimeslotLabPintarWizard(models.TransientModel):
    _name = "create.timeslot.labpintar.wizard"
    _description = 'Lab Pintar Create Timeslot Wizard'

    start_date = fields.Date('Start Date',required=True, default=fields.Date.context_today)
    end_date = fields.Date('End Date',required=True, default=fields.Date.context_today)
    time_string = fields.Text('Time',default='08:00,09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,18:00')

    id_time_vendor = fields.Text('ID Time Vendor', default='')
    id_jenis_tindakan_vendor = fields.Text('ID Jenis Tindakan Vendor', default='')

    timeslot_type = fields.Selection([('home_care', 'Home Care'), ('group_booking', 'Group Booking')], 'Timeslot Type', default='home_care',
                                     required=True)
    total_timeslot = fields.Integer('Total Timeslot', default=5, required=True)

    antigen_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_wizard_antigen_rel','timeslot_antigen_wizard_id', 'price_list_id', 'Antigen')

    pcr_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_wizard_pcr_rel','timeslot_pcr_wizard_id', 'price_list_id', 'PCR')

    pcr_express_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_wizard_pcr_express_rel',
                                     'timeslot_pcr_express_wizard_id', 'price_list_id', 'PCR Express')

    pcr_priority_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_wizard_pcr_priority_rel',
                                     'timeslot_pcr_priority_wizard_id', 'price_list_id', 'PCR Priority')

    srbd_price_ids = fields.Many2many('tt.price.list.labpintar', 'tt_price_list_labpintar_price_wizard_srbd_rel',
                                     'timeslot_srbd_wizard_id', 'price_list_id', 'SRBD')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    single_supplement = fields.Monetary('Single Supplement', default=SINGLE_SUPPLEMENT, required=True)
    overtime_surcharge = fields.Monetary('Overtime Surcharge', default=OVERTIME_SURCHARGE, required=True)
    cito_surcharge = fields.Monetary('Cito Surcharge', default=CITO_SURCHARGE, required=True)

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    agent_id = fields.Many2one('tt.agent', 'Agent')
    default_data_id = fields.Many2one('tt.timeslot.labpintar.default', 'Default Data')

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
        self.pcr_express_price_ids = self.default_data_id.pcr_express_price_ids
        self.pcr_priority_price_ids = self.default_data_id.pcr_priority_price_ids
        self.srbd_price_ids = self.default_data_id.srbd_price_ids
        self.single_supplement = self.default_data_id.single_supplement
        self.overtime_surcharge = self.default_data_id.overtime_surcharge
        self.cito_surcharge = self.default_data_id.cito_surcharge
        self.time_string = self.default_data_id.time_string

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
        return [('provider_type_id','=',self.env.ref('tt_reservation_labpintar.tt_provider_type_labpintar').id)]

    area_id = fields.Many2one('tt.destinations', 'Area', domain=_get_area_id_domain, required=True)

    def generate_timeslot(self, from_cron=False):
        date_delta = self.end_date - self.start_date
        date_delta = date_delta.days+1
        create_values = []
        timelist = self.time_string.split(',')
        id_timelist_labpintar = self.id_time_vendor.split(',')

        #price list
        antigen_list = False
        pcr_list = False
        pcr_express_list = False
        pcr_priority_list = False
        srbd_list = False

        if from_cron:
            data_default = self.env.ref('tt_reservation_labpintar.tt_timeslot_labpintar_default_data')
            antigen_list = [(6, 0, [x.id for x in data_default.antigen_price_ids])]
            pcr_list = [(6, 0, [x.id for x in data_default.pcr_price_ids])]
            pcr_express_list = [(6, 0, [x.id for x in data_default.pcr_express_price_ids])]
            pcr_priority_list = [(6, 0, [x.id for x in data_default.pcr_priority_price_ids])]
            srbd_list = [(6, 0, [x.id for x in data_default.srbd_price_ids])]
        else:
            if self.antigen_price_ids:
                antigen_list = [(6, 0, [x.id for x in self.antigen_price_ids])]
            if self.pcr_price_ids:
                pcr_list = [(6, 0, [x.id for x in self.pcr_price_ids])]
            if self.pcr_express_price_ids:
                pcr_express_list = [(6, 0, [x.id for x in self.pcr_express_price_ids])]
            if self.pcr_priority_price_ids:
                pcr_priority_list = [(6, 0, [x.id for x in self.pcr_priority_price_ids])]
            if self.srbd_price_ids:
                srbd_list = [(6, 0, [x.id for x in self.srbd_price_ids])]

        ##convert to timezone 0
        time_objs = []
        time_objs_id_labpintar = []
        for idx, time_str in enumerate(timelist):
            time_objs.append((datetime.strptime(time_str,'%H:%M') - timedelta(hours=7)).time())
            time_objs_id_labpintar.append(id_timelist_labpintar[idx] if len(id_timelist_labpintar) > idx else id_timelist_labpintar[0])

        db = self.env['tt.timeslot.labpintar'].search([('destination_id','=',self.area_id.id), ('dateslot','>=',self.start_date), ('dateslot','<=',self.end_date), ('timeslot_type','=',self.timeslot_type), ('agent_id','=',self.agent_id.id if self.agent_id else False)])
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
                        'total_timeslot': self.total_timeslot,
                        'currency_id': self.currency_id.id,
                        'timeslot_type': self.timeslot_type,
                        'antigen_price_ids': antigen_list,
                        'pcr_price_ids': pcr_list,
                        'pcr_express_price_ids': pcr_express_list,
                        'pcr_priority_price_ids': pcr_priority_list,
                        'srbd_price_ids': srbd_list,
                        'single_supplement': data_default.single_supplement,
                        'overtime_surcharge': data_default.overtime_surcharge,
                        'cito_surcharge': data_default.cito_surcharge,
                        'agent_id': self.agent_id.id if self.agent_id else False,
                    })

        self.env['tt.timeslot.labpintar'].create(create_values)