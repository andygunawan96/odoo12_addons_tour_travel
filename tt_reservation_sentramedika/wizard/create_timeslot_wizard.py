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
ADDRESS_SURCHARGE = 100000## Urgent cito surcharge range 2-5jam stlh jam book

class CreateTimeslotSentraMedikaWizard(models.TransientModel):
    _name = "create.timeslot.sentramedika.wizard"
    _description = 'Sentra Medika Create Timeslot Wizard'

    start_date = fields.Date('Start Date',required=True, default=fields.Date.context_today)
    end_date = fields.Date('End Date',required=True, default=fields.Date.context_today)
    time_string = fields.Text('Time',default='08:00,09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00')

    id_time_vendor = fields.Text('ID Time Vendor', default='')
    id_jenis_tindakan_vendor = fields.Text('ID Jenis Tindakan Vendor', default='')

    timeslot_type = fields.Selection([('home_care', 'Home Care'), ('group_booking', 'Group Booking')], 'Timeslot Type', default='home_care',
                                     required=True)
    total_timeslot = fields.Integer('Total Timeslot', default=5, required=True)

    antigen_price_ids = fields.Many2many('tt.price.list.sentramedika', 'tt_price_list_sentramedika_price_wizard_antigen_rel','timeslot_antigen_wizard_id', 'price_list_id', 'Antigen')

    pcr_price_ids = fields.Many2many('tt.price.list.sentramedika', 'tt_price_list_sentramedika_price_wizard_pcr_rel','timeslot_pcr_wizard_id', 'price_list_id', 'PCR')

    mcu_price_ids = fields.Many2many('tt.price.list.sentramedika', 'tt_price_list_sentramedika_price_wizard_mcu_rel','timeslot_mcu_wizard_id', 'price_list_id', 'MCU')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    additional_price = fields.Monetary('Tambahan Peduli Lindungi')

    single_supplement = fields.Monetary('Single Supplement', default=SINGLE_SUPPLEMENT, required=True)
    overtime_surcharge = fields.Monetary('Overtime Surcharge', default=OVERTIME_SURCHARGE, required=True)
    cito_surcharge = fields.Monetary('Cito Surcharge', default=CITO_SURCHARGE, required=True)
    address_surcharge = fields.Monetary('Cito Surcharge', default=ADDRESS_SURCHARGE, required=True)

    agent_id = fields.Many2one('tt.agent', 'Agent')
    default_data_id = fields.Many2one('tt.timeslot.sentramedika.default', 'Default Data')

    # @api.model
    # def create(self, vals_list):
    #     new_rec = super(CreateTimeslotphcWizard, self).create(vals_list)
    #     if new_rec.default_data_id:
    #         new_rec.commission_antigen = new_rec.default_data_id.commission_antigen
    #         new_rec.commission_pcr = new_rec.default_data_id.commission_pcr
    #         new_rec.commission_mcu = new_rec.default_data_id.commission_mcu
    #         new_rec.commission_pcr_express = new_rec.default_data_id.commission_pcr_express
    #         new_rec.commission_srbd = new_rec.default_data_id.commission_srbd
    #         new_rec.base_price_antigen = new_rec.default_data_id.base_price_antigen
    #         new_rec.base_price_pcr = new_rec.default_data_id.base_price_pcr
    #         new_rec.base_price_pcr_dt = new_rec.default_data_id.base_price_pcr_dt
    #         new_rec.base_price_mcu = new_rec.default_data_id.base_price_mcu
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
        self.mcu_price_ids = self.default_data_id.mcu_price_ids
        self.single_supplement = self.default_data_id.single_supplement
        self.overtime_surcharge = self.default_data_id.overtime_surcharge
        self.cito_surcharge = self.default_data_id.cito_surcharge
        self.address_surcharge = self.default_data_id.address_surcharge
        self.additional_price = self.default_data_id.additional_price
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
        return [('provider_type_id','=',self.env.ref('tt_reservation_sentramedika.tt_provider_type_sentramedika').id)]

    area_id = fields.Many2one('tt.destinations', 'Area', domain=_get_area_id_domain, required=True)

    def generate_timeslot(self, from_cron=False):
        date_delta = self.end_date - self.start_date
        date_delta = date_delta.days+1
        create_values = []
        timelist = self.time_string.split(',')

        #price list
        antigen_list = False
        pcr_list = False
        mcu_list = False
        if from_cron == True:
            if self.area_id.code == 'SUB':
                default_data = self.env.ref('tt_reservation_sentramedika.tt_timeslot_sentramedika_default_data')

            antigen_list = [(6, 0, [x.id for x in default_data.antigen_price_ids])]
            pcr_list = [(6, 0, [x.id for x in default_data.pcr_price_ids])]
            mcu_list = [(6, 0, [x.id for x in default_data.mcu_price_ids])]
            additional_price = default_data.additional_price
            single_supplement = default_data.single_supplement
            overtime_surcharge = default_data.overtime_surcharge
            cito_surcharge = default_data.cito_surcharge
            address_surcharge = default_data.address_surcharge
            address_surcharge = default_data.address_surcharge
        else:
            if self.antigen_price_ids:
                antigen_list = [(6, 0, [x.id for x in self.antigen_price_ids])]
            if self.pcr_price_ids:
                pcr_list = [(6, 0, [x.id for x in self.pcr_price_ids])]
            if self.mcu_price_ids:
                mcu_list = [(6, 0, [x.id for x in self.mcu_price_ids])]
            additional_price = self.additional_price
            single_supplement = self.single_supplement
            overtime_surcharge = self.overtime_surcharge
            cito_surcharge = self.cito_surcharge
            address_surcharge = self.address_surcharge

        ##convert to timezone 0
        time_objs = []
        for idx, time_str in enumerate(timelist):
            time_objs.append((datetime.strptime(time_str,'%H:%M') - timedelta(hours=7)).time())

        db = self.env['tt.timeslot.sentramedika'].search([('destination_id','=',self.area_id.id), ('dateslot','>=',self.start_date), ('dateslot','<=',self.end_date), ('timeslot_type','=',self.timeslot_type), ('agent_id','=',self.agent_id.id if self.agent_id else False)])
        db_list = [str(data.datetimeslot) for data in db]
        for this_date_counter in range(date_delta):
            for idx, this_time in enumerate(time_objs):
                this_date = self.start_date + timedelta(days=this_date_counter)
                datetimeslot = datetime.strptime('%s %s' % (str(this_date),this_time),'%Y-%m-%d %H:%M:%S')
                if datetimeslot.strftime('%A') != 'Sunday' or datetimeslot.strftime('%A') == 'Sunday' and datetimeslot.strftime('%H:%M') != '19:00':
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
                            'mcu_price_ids': mcu_list,
                            'additional_price': additional_price,
                            'single_supplement': single_supplement,
                            'overtime_surcharge': overtime_surcharge,
                            'cito_surcharge': cito_surcharge,
                            'address_surcharge': address_surcharge,
                            'agent_id': self.agent_id.id if self.agent_id else False,
                        })

        self.env['tt.timeslot.sentramedika'].create(create_values)