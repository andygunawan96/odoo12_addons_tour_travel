from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import image
from ...tools import test_to_dict

class TtCustomer(models.Model,test_to_dict.ToDict):
    _inherit = 'tt.history'
    _name = 'tt.customer'
    _rec_name = 'name'
    _description = 'Tour & Travel - Customer'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    logo = fields.Binary('Agent Logo', attachment=True)
    logo_thumb = fields.Binary('Agent Logo Thumb', compute="_get_logo_image", store=True, attachment=True)

    active = fields.Boolean('Active', default=True)
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    nickname = fields.Char('Nickname')
    title = fields.Selection([('MR', 'Mr.'), ('MSTR', 'Mstr.'), ('MRS', 'Mrs.'), ('MS', 'Ms.'), ('MISS', 'Miss')],
                             string='Title')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    marital_status = fields.Selection([('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced'),
                                       ('widowed', 'Widowed')], 'Marital Status')
    religion = fields.Selection([('islam', 'Islam'), ('protestantism', 'Protestantism'), ('catholicism', 'Catholicism'),
                                 ('hinduism', 'Hinduism'), ('buddhism', 'Buddhism'), ('confucianism', 'Confucianism'),
                                 ('others', 'Others')], 'Religion')
    birth_date = fields.Date('Birth Date')
    age = fields.Char('Age', help='For Adult, age in year\nFor Child, age in month',
                      compute="calculate_age")
    address_ids = fields.One2many('address.detail', 'customer_id', 'Social Media Detail')
    phone_ids = fields.One2many('phone.detail', 'customer_id', 'Social Media Detail')
    social_media_ids = fields.One2many('social.media.detail', 'customer_id', 'Social Media Detail')
    employment_ids = fields.One2many('res.employee', 'customer_id', 'Employee')
    email = fields.Char('Email')
    passport_number = fields.Char(string='Passport Number')
    passport_exp_date = fields.Datetime(string='Passport Exp Date')
    user_id = fields.One2many('res.users', 'customer_id', 'User')
    customer_bank_detail_ids = fields.One2many('customer.bank.detail', 'customer_id', 'Customer Bank Detail')

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        self.name = "%s %s" % (self.first_name, self.last_name)

    @api.onchange('birth_date')
    def calculate_age(self):
        if self.birth_date:
            d1 = datetime.strptime(str(self.birth_date), "%Y-%m-%d").date()
            d2 = datetime.today()
            self.age = relativedelta(d2, d1).years
            return self.age

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

