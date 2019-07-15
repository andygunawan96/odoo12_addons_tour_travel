from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import image
from ...tools import variables


class TtCustomer(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer'
    _rec_name = 'name'
    _description = 'Tour & Travel - Customer'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    logo = fields.Binary('Agent Logo', attachment=True)
    logo_thumb = fields.Binary('Agent Logo Thumb', compute="_get_logo_image", store=True, attachment=True)

    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    nickname = fields.Char('Nickname')

    gender = fields.Selection(variables.GENDER, string='Gender')

    marital_status = fields.Selection(variables.MARITAL_STATUS, 'Marital Status')
    religion = fields.Selection(variables.RELIGION, 'Religion')

    nationality_id = fields.Many2one('tt.country','Nationality')

    birth_date = fields.Date('Birth Date')
    age = fields.Char('Age', help='For Adult, age in year\nFor Child, age in month',
                      compute="calculate_age")
    nationality_id = fields.Many2one('res.country', 'Nationality')
    country_of_issued_id = fields.Many2one('res.country', 'Country of Issued')
    address_ids = fields.One2many('address.detail', 'customer_id', 'Address Detail')
    phone_ids = fields.One2many('phone.detail', 'customer_id', 'Phone Detail')
    social_media_ids = fields.One2many('social.media.detail', 'customer_id', 'Social Media Detail')
    employment_ids = fields.One2many('res.employee', 'customer_id', 'Employee')
    email = fields.Char('Email')
    identity_type = fields.Selection(variables.IDENTITY_TYPE,'Identity Type')
    identity_number = fields.Char('Identity Number')
    passport_number = fields.Char(string='Passport Number')
    passport_expdate = fields.Datetime(string='Passport Exp Date')
    user_id = fields.One2many('res.users', 'customer_id', 'User')
    customer_bank_detail_ids = fields.One2many('customer.bank.detail', 'customer_id', 'Customer Bank Detail')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    customer_parent_ids = fields.Many2many('tt.customer.parent','tt_customer_customer_parent_rel','customer_id','customer_parent_id','Customer_parent')
    can_book = fields.Boolean('Is Booker', default=False)

    active = fields.Boolean('Active', default=True)

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        self.name = "%s %s" % (self.first_name, self.last_name)

    @api.onchange('birth_date')
    def calculate_age(self):
        for rec in self:
            if rec.birth_date:
                d1 = datetime.strptime(str(rec.birth_date), "%Y-%m-%d").date()
                d2 = datetime.today()
                rec.age = relativedelta(d2, d1).years
        return rec.age

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

    # @api.multi
    # def write(self, value):
    #     self_dict = self.read()
    #     key_list = [key for key in value.keys()]
    #     for key in key_list:
    #         print(self.fields_get().get(key)['string'])
    #         self.message_post(body=_("%s has been changed from %s to %s by %s.") %
    #                                 (self.fields_get().get(key)['string'],  # Model String / Label
    #                                  self_dict[0].get(key),  # Old Value
    #                                  value[key],  # New Value
    #                                  self.env.user.name))  # User that Changed the Value
    #     return super(TtCustomer, self).write(value)

