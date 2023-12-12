import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools.ERR import RequestException
from ...tools import ERR
import logging,traceback


TYPE = [
    ('work', 'Work'),
    ('home', 'Home'),
    ('mobile', 'Mobile'),
    ('other', 'Other')
]

_logger = logging.getLogger(__name__)

class PhoneDetail(models.Model):
    _name = 'phone.detail'
    _description = 'Tour & Travel - Phone Detail'
    _order = 'last_updated_time desc'

    type = fields.Selection(TYPE, 'Phone Type', required=True, default='work')
    description = fields.Char('Description')
    country_id = fields.Many2one('res.country', string='Country')
    calling_code = fields.Char('Calling Code', required=True)
    calling_number = fields.Char('Calling Number', required=True)
    phone_number = fields.Char('Phone Number', store=True, compute='_compute_phone_number')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', string='Agent')
    provider_ho_data_id = fields.Many2one('tt.provider.ho.data', string='Provider HO Data')
    customer_id = fields.Many2one('tt.customer', string='Customer',ondelete="cascade")
    customer_parent_id = fields.Many2one('tt.customer.parent', string='Customer Parent')
    va_create = fields.Boolean('VA Create', default=False)
    active = fields.Boolean('Active', default=True)
    last_updated_time = fields.Integer('Last Update',default=0)

    @api.model
    def create(self, vals_list):
        vals_list['last_updated_time'] = time.time()
        return super(PhoneDetail, self).create(vals_list)

    def to_dict(self):
        return {
            'type': self.type,
            'calling_code': self.calling_code,
            'calling_number': self.calling_number,
        }

    @api.depends('calling_code', 'calling_number')
    @api.onchange('calling_code', 'calling_number')
    def _compute_phone_number(self):
        for rec in self:
            rec.phone_number = (rec.calling_code and rec.calling_code or '') + (rec.calling_number and rec.calling_number or '')

    def create_va_number_api(self, data, context):
        agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
        try:
            agent_obj.create_date
        except:
            raise RequestException(1008)

        payment_acq_number_obj = agent_obj.payment_acq_ids.filtered(lambda x: x.state == 'open')
        if payment_acq_number_obj:
            return ERR.get_error(500, "Please delete your old VA!")

        if data.get('email'):
            agent_obj.email = data['email']

        phone_obj = agent_obj.phone_ids.filtered(lambda x: x.calling_number == data['calling_number'])
        if not phone_obj:
            phone_obj = [self.create({
                "type": 'work',
                "calling_code": data['calling_code'],
                "calling_number": data['calling_number'],
                "ho_id": context['co_ho_id'],
                "agent_id": agent_obj.id
            })]
        try:
            phone_obj[0].generate_va_number()
        except Exception as e:
            return ERR.get_error(500, additional_message=str(e.name))
        return ERR.get_no_error()

    def generate_va_number(self):
        agent_open_payment_acqurier = self.env['payment.acquirer.number'].search([
            ('agent_id','=',self.agent_id.id),
            ('state','=','open')
        ])
        agent_obj = self.env['tt.agent'].search([('id', '=', self.agent_id.id)])
        check_number = self.env['payment.acquirer.number'].search([('ho_id','=', agent_obj.ho_id.id), '|', ('number', 'ilike', self.calling_number[-8:]), ('email', '=', agent_obj.email)])
        if len(check_number) == 0 and len(agent_open_payment_acqurier) == 0 and agent_obj.email and agent_obj.name:
            ho_obj = agent_obj.ho_id
            bank_code_list = []
            provider_payment_list = []
            existing_payment_acquirer_open = self.env['payment.acquirer'].search([('agent_id', '=', ho_obj.id), ('type', '=', 'va')])
            for rec in existing_payment_acquirer_open:
                bank_code_list.append(rec.bank_id.code)
                if rec.provider_id:
                    if rec.provider_id.code not in provider_payment_list:
                        provider_payment_list.append(rec.provider_id.code)
            currency_obj = self.agent_id.ho_id.currency_id
            data = {
                'number': self.calling_number[-8:],
                'email': agent_obj.email,
                'name': agent_obj.name,
                'bank_code_list': bank_code_list,
                'currency': currency_obj.name
            }
            for provider_payment in provider_payment_list:
                data.update({
                    "provider": provider_payment
                })
                res = self.env['tt.payment.api.con'].set_VA(data, ho_obj.id)
                # res = self.env['tt.payment.api.con'].test(data)
                # res = self.env['tt.payment.api.con'].delete_VA(data)
                # res = self.env['tt.payment.api.con'].set_invoice(data)
                # res = self.env['tt.payment.api.con'].merchant_info(data)
                if res['error_code'] == 0:
                    if len(res['response']) > 0:
                        for rec in res['response']:
                            bank_obj = self.env['tt.bank'].search([('code', '=', rec['code'])],limit=1)
                            existing_payment_acquirer = self.env['payment.acquirer'].search([('agent_id','=',ho_obj.id), ('type','=','va'), ('bank_id','=',bank_obj.id)])
                            if not existing_payment_acquirer:
                                existing_payment_acquirer = self.env['payment.acquirer'].create({
                                    'type': 'va',
                                    'bank_id': bank_obj.id,
                                    'agent_id': ho_obj.id,
                                    'provider': 'manual',
                                    'website_published': False,
                                    'name': 'Your Virtual Account at %s' % (bank_obj.name),
                                })
                            self.env['payment.acquirer.number'].create({
                                'agent_id': agent_obj.id,
                                'payment_acquirer_id': existing_payment_acquirer.id,
                                'state': 'open',
                                'number': rec['number'],
                                'email': agent_obj.email,
                                'currency_id': currency_obj.id,
                                'ho_id': agent_obj.ho_id.id
                            })
                    else:
                        raise UserError(_("Phone number has been use, please change first phone number"))
                    for rec in agent_obj.phone_ids:
                        rec.va_create = False
                    self.va_create = True
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
            else:
                raise UserError(_(res['error_msg']))
        elif not agent_obj.email:
            raise UserError(_("Please fill email"))
        elif not agent_obj.name:
            raise UserError(_("Please fill agent name"))
        elif len(check_number) > 0:
            raise UserError(_("Phone number or email has been registered in our system please use other number"))
        elif len(agent_open_payment_acqurier) > 0:
            raise UserError(_("You have already registered a VA account"))

    def delete_va_number(self):

        agent_obj = self.env['tt.agent'].search([('id', '=', self.agent_id.id)])
        ho_obj = agent_obj.ho_id
        bank_code_list = []
        provider_payment_list = []
        existing_payment_acquirer_open = self.env['payment.acquirer'].search([('ho_id','=', ho_obj.id),('agent_id', '=', ho_obj.id), ('type', '=', 'va')])
        for rec in existing_payment_acquirer_open:
            bank_code_list.append(rec.bank_id.code)
            if rec.provider_id:
                if rec.provider_id.code not in provider_payment_list:
                    provider_payment_list.append(rec.provider_id.code)
        currency_name = self.agent_id.ho_id.currency_id.name
        data = {
            "number": self.calling_number[-8:],
            'email': agent_obj.email,
            'name': agent_obj.name,
            'bank_code_list': bank_code_list,
            'currency': currency_name
        }
        self.va_create = False
        self.env.cr.commit()
        if len(data) != 0:
            for provider_payment in provider_payment_list:
                data.update({
                    "provider": provider_payment
                })
                res = self.env['tt.payment.api.con'].delete_VA(data, agent_obj.ho_id.id)
                if res['error_code'] == 0:
                    for rec in self.env['tt.agent'].search([('id', '=', self.agent_id.id)]).payment_acq_ids.filtered(lambda x: x.state == 'open'):
                        rec.unlink()
                    self.va_create = False
                    self.env.cr.commit()
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
            else:
                raise UserError(_("Error delete VA !"))
        else:
            raise UserError(_("No Such data VA !"))

    def compute_number(self):
        self._compute_phone_number()
