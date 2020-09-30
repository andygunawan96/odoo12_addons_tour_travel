from odoo import api, fields, models, _
from odoo.exceptions import UserError

TYPE = [
    ('work', 'Work'),
    ('home', 'Home'),
    ('other', 'Other')
]


class PhoneDetail(models.Model):
    _name = 'phone.detail'
    _description = 'Tour & Travel - Phone Detail'

    type = fields.Selection(TYPE, 'Phone Type', required=True, default='work')
    country_id = fields.Many2one('res.country', string='Country')
    calling_code = fields.Char('Calling Code', required=True)
    calling_number = fields.Char('Calling Number', required=True)
    phone_number = fields.Char('Phone Number', readonly=True, compute='_compute_phone_number')
    agent_id = fields.Many2one('tt.agent', string='Agent')
    customer_id = fields.Many2one('tt.customer', string='Customer')
    customer_parent_id = fields.Many2one('tt.customer.parent', string='Customer Parent')
    va_create = fields.Boolean('VA Create', default=False)
    active = fields.Boolean('Active', default=True)

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

    def generate_va_number(self):
        check_number = self.env['payment.acquirer.number'].search([('number', 'ilike', self.calling_number[-8:])])
        agent_open_payment_acqurier = self.env['payment.acquirer.number'].search([
            ('agent_id','=',self.agent_id.id),
            ('state','=','open')
        ])
        agent = self.env['tt.agent'].search([('id', '=', self.agent_id.id)])
        if len(check_number) == 0 and len(agent_open_payment_acqurier) == 0 and agent.email and agent.name:
            data = {
                'number': self.calling_number[-8:],
                'email': agent.email,
                'name': agent.name
            }
            res = self.env['tt.payment.api.con'].set_VA(data)
            # res = self.env['tt.payment.api.con'].test(data)
            # res = self.env['tt.payment.api.con'].delete_VA(data)
            # res = self.env['tt.payment.api.con'].set_invoice(data)
            # res = self.env['tt.payment.api.con'].merchant_info(data)
            if res['error_code'] == 0:
                if len(res['response']) > 0:
                    ho_agent_obj = self.env['tt.agent'].browse(self.env.ref('tt_base.rodex_ho').id)
                    for rec in res['response']:
                        bank_obj = self.env['tt.bank'].search([('name', '=ilike', rec['bank'])],limit=1)
                        existing_payment_acquirer = self.env['payment.acquirer'].search([('agent_id','=',ho_agent_obj.id),('name','=','Virtual Account %s' % (bank_obj.name))])
                        if not existing_payment_acquirer:
                            existing_payment_acquirer = self.env['payment.acquirer'].create({
                                'type': 'va',
                                'bank_id': bank_obj.id,
                                'agent_id': ho_agent_obj.id,
                                'provider': 'manual',
                                'website_published': False,
                                'name': 'Virtual Account %s' % (bank_obj.name),
                            })
                        self.env['payment.acquirer.number'].create({
                            'agent_id': agent.id,
                            'payment_acquirer_id': existing_payment_acquirer.id,
                            'state': 'open',
                            'number': rec['number']
                        })
                        for rec in agent.phone_ids:
                            rec.va_create = False
                        self.va_create = True
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'reload',
                        }
                else:
                    raise UserError(_("Phone number has been use, please change first phone number"))
            else:
                raise UserError(_(res['error_msg']))
        elif not agent.email:
            raise UserError(_("Please fill email"))
        elif not agent.name:
            raise UserError(_("Please fill agent name"))
        elif len(check_number) > 0:
            raise UserError(_("Phone number has been register in our system please use other number"))
        elif len(agent_open_payment_acqurier) > 0:
            raise UserError(_("You have register VA account"))


    def delete_va_number(self):
        data = {
            "number": self.calling_number[-8:]
        }
        self.va_create = False
        self.env.cr.commit()
        if len(data) != 0:
            res = self.env['tt.payment.api.con'].delete_VA(data)
            if res['error_code'] == 0:
                for rec in self.env['tt.agent'].search([('id', '=', self.agent_id.id)]).payment_acq_ids:
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
