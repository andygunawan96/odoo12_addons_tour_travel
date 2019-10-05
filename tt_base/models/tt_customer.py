from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
from odoo.tools import image
from ...tools import variables,util,ERR
import json,time
import logging,traceback

_logger = logging.getLogger(__name__)

class TtCustomer(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer'
    _rec_name = 'name'
    _description = 'Tour & Travel - Customer'

    seq_id = fields.Char('ID')
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    logo = fields.Binary('Agent Logo', attachment=True)
    logo_thumb = fields.Binary('Agent Logo Thumb', compute="_get_logo_image", store=True, attachment=True)
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    nickname = fields.Char('Nickname')
    gender = fields.Selection(variables.GENDER, string='Gender')
    marital_status = fields.Selection(variables.MARITAL_STATUS, 'Marital Status')
    religion = fields.Selection(variables.RELIGION, 'Religion')
    birth_date = fields.Date('Birth Date')
    nationality_id = fields.Many2one('res.country', 'Nationality')
    country_of_issued_id = fields.Many2one('res.country', 'Country of Issued')
    address_ids = fields.One2many('address.detail', 'customer_id', 'Address Detail')
    phone_ids = fields.One2many('phone.detail', 'customer_id', 'Phone Detail')
    social_media_ids = fields.One2many('social.media.detail', 'customer_id', 'Social Media Detail')
    email = fields.Char('Email')
    identity_type = fields.Selection(variables.IDENTITY_TYPE, 'Identity Type')
    identity_number = fields.Char('Identity Number')
    passport_number = fields.Char(string='Passport Number')
    passport_expdate = fields.Datetime(string='Passport Exp Date')
    user_ids = fields.One2many('res.users', 'customer_id', 'User')
    customer_bank_detail_ids = fields.One2many('customer.bank.detail', 'customer_id', 'Customer Bank Detail')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    customer_parent_ids = fields.Many2many('tt.customer.parent','tt_customer_customer_parent_rel','customer_id','customer_parent_id','Customer Parent')

    active = fields.Boolean('Active', default=True)

    identity_ids = fields.One2many('tt.customer.identity','customer_id','Identity List')

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        self.name = "%s %s" % (self.first_name and self.first_name or '', self.last_name and self.last_name or '')

    @api.depends('logo')
    def _get_logo_image(self):
        for record in self:
            if record.logo:
                record.logo_thumb = image.crop_image(record.logo, type='center', ratio=(4, 3), size=(200, 200))
            else:
                record.logo_thumb = False

    @api.multi
    def set_history_message(self):
        for rec in self:
            body = "Message has been approved on %s", datetime.now()
            rec.message_post(body=body)

    @api.model
    def create(self, vals_list):
        util.pop_empty_key(vals_list)
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.customer')
        return super(TtCustomer, self).create(vals_list)

    def to_dict(self):
        phone_list = []
        for rec in self.phone_ids:
            phone_list.append(rec.to_dict())
        res = {
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name and self.last_name or '',
            'gender': self.gender and self.gender or '',
            'birth_date': self.birth_date and self.birth_date.strftime('%Y-%m-%d') or '',
            'nationality_code': self.nationality_id and self.nationality_id.code or '',
            'nationality_name': self.nationality_id and self.nationality_id.name or '',
            'country_of_issued_code': self.country_of_issued_id and self.country_of_issued_id.code or '',
            'country_of_issued_name': self.country_of_issued_id and self.country_of_issued_id.name or '',
            'passport_expdate': self.passport_expdate and self.passport_expdate.strftime('%Y-%m-%d') or '',
            'passport_number': self.passport_number and self.passport_number or '',
            'marital_status': self.marital_status and self.marital_status or '',
            'phones': phone_list,
            'email': self.email and self.email or '',
            'seq_id': self.seq_id
        }
        return res

    def copy_to_passenger(self):
        res = {
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'gender': self.gender,
            'birth_date': self.birth_date.strftime('%Y-%m-%d'),
            'nationality_code': self.nationality_id.id,
            'country_of_issued_id': self.country_of_issued_id.id,
            'identity_type': self.identity_type,
            'identity_number': self.identity_number,
            'customer_id': self.id,
        }
        return res

    def get_customer_list_api(self,req,context):
        try:
            print("request teropong\n"+json.dumps((req))+json.dumps(context))
            customer_list_obj = self.search([('agent_id','=',context['co_agent_id']),('name','ilike',req['name'])])
            customer_list = []
            if req.get('lower') and req.get('upper'):
                lower = date.today() - relativedelta(years=req.get('lower'))
                upper = date.today() - relativedelta(years=req.get('upper'))
            else:
                lower = date.today() - relativedelta(years=17)
                upper = date.today() - relativedelta(years=200)
            for cust in customer_list_obj:
                ###fixme kalau tidak pbirth_date gimana? di asumsikan adult?
                if cust.birth_date:
                    if not (upper <= cust.birth_date <= lower):
                        continue
                values = cust.to_dict()
                customer_list.append(values)
            _logger.info(json.dumps(customer_list))
            return ERR.get_no_error(customer_list)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error()

    def add_identity_button(self):
        self.add_or_update_identity('ktp',time.time())

    def add_or_update_identity(self,name,number):
        not_exist =True

        for identity in self.identity_ids:
            if identity.name == name:
                not_exist = False
                exixting_identity = identity
                break

        if not_exist:
            self.env['tt.customer.identity'].create({
                'name': name,
                'number': number,
                'customer_id': self.id
            })
        else:
            exixting_identity.update({
                'number': number
            })



class TtCustomerIdentityNumber(models.Model):
    _name = "tt.customer.identity"
    _description = "Customer Identity Type"

    name = fields.Selection([('ktp','KTP'),
                             ('passport','Passport'),
                             ('sim','SIM'),
                             ('other','Other')],'Type',required=True)

    number = fields.Char('Number',required=True)

    customer_id = fields.Many2one('tt.customer','Owner',required=True)

    def create(self, vals_list):
        new_identity = super(TtCustomerIdentityNumber, self).create(vals_list)
        ##validator tidak kembar
        if len(new_identity.ids) >1:
            identity = new_identity[0]
        else:
            identity = new_identity

        identity_list = identity.customer_id.identity_ids
        for id1 in identity_list:
            for id2 in identity_list:
                if id1.name == id2.name and id1.id != id2.id:
                    raise UserError ('%s|%s Already Exists.' % (id1.id,id1.name))

        return new_identity