from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError
from ...tools.api import Response
import base64
import copy
import logging
import traceback
from ...tools.api import Response

_logger = logging.getLogger(__name__)

COMPANY_TYPE = [
    ('individual', 'Individual'),
    ('company', 'Company')
]

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('progress', 'Surveying'),
    ('payment', 'Payment'),
    ('validate', 'Validate'),
    ('done', 'Done'),
    ('cancel', 'Cancel')
]


class AgentRegistration(models.Model):
    _name = 'tt.agent.registration'
    _description = 'Rodex Model'
    _order = 'registration_num desc'

    name = fields.Char('Name', default='')
    image = fields.Binary('Image', store=True)
    state = fields.Selection(STATE, 'State', default='draft',
                             help='''draft = Requested
                                     confirm = HO Accepted
                                     progress = HO Processing
                                     payment = Payment
                                     validate = Validate
                                     done = Done''')
    active = fields.Boolean('Active', default=True)
    parent_agent_id = fields.Many2one('tt.agent', string="Parent Agent", Help="Agent who became Parent of This Agent",
                                      readonly=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True, readonly=True,
                                    states={'draft': [('readonly', False)],
                                            'confirm': [('readonly', False)]})
    agent_id = fields.Many2one('tt.agent', 'Agent ID', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_type = fields.Selection(COMPANY_TYPE, 'Company Type', default='individual')
    registration_num = fields.Char('Registration No.', readonly=True)
    registration_fee = fields.Float('Registration Fee', store=True, compute='get_registration_fee')
    # promotion_id required supaya agent yang merekrut bisa dapat komisi
    promotion_id = fields.Many2one('tt.agent.registration.promotion', 'Promotion', readonly=True, required=True,
                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                   domain=lambda self: [("agent_type_id", "=", self.env.user.agent_id.agent_type_id.id),
                                                        ("start_date", "<=", date.today().strftime('%d/%m/%Y')),
                                                        ("end_date", ">=", date.today().strftime('%d/%m/%Y'))])
    discount = fields.Float('Discount', readonly=True, compute='compute_discount')
    opening_balance = fields.Float('Opening Balance', readonly=True, states={'draft': [('readonly', False)],
                                                                             'confirm': [('readonly', False)]})
    total_fee = fields.Monetary('Total Fee', compute='compute_total_fee')
    registration_date = fields.Datetime('Registration Date', required=True, readonly=True,
                                        states={'draft': [('readonly', False)]})
    expired_date = fields.Date('Expired Date', readonly=True, states={'draft': [('readonly', False)]})

    business_license = fields.Char('Business License')
    tax_identity_number = fields.Char('NPWP')

    address_ids = fields.One2many('address.detail', 'agent_registration_id', string='Addresses')
    social_media_ids = fields.One2many('social.media.detail', 'agent_registration_id', 'Social Media')

    # agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', readonly=True, required=True,
    #                                 states={'draft': [('readonly', False)]})
    reference_id = fields.Many2one('tt.agent', 'Reference', readonly=True, default=lambda self: self.env.user.agent_id)
    # parent_agent_id = fields.Many2one('tt.agent', 'Parent Agent', readonly=True, store=True,
    #                                   compute='default_parent_agent_id')
    agent_level = fields.Integer('Agent Level', readonly=True)

    issued_uid = fields.Many2one('res.users', 'Issued by', readonly=True)
    issued_date = fields.Datetime('Issued Date', readonly=True)

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', readonly=True,
                                 domain=[('res_model', '=', 'tt.agent.registration')])

    contact_ids = fields.One2many('tt.customer', 'agent_registration_id', 'Contact Information')

    agent_registration_customer_ids = fields.One2many('tt.agent.registration.customer', 'agent_registration_id',
                                                      'Agent Registration Contact')

    registration_document_ids = fields.One2many('tt.agent.registration.document', 'registration_document_id',
                                                'Agent Registration Documents', readonly=True,
                                                states={'confirm': [('readonly', False)]},
                                                help='''Dokumen yang perlu dilengkapi saat pendaftaran, seperti KTP, NPWP, dll''')

    payment_ids = fields.One2many('tt.agent.registration.payment', 'agent_registration_id', 'Payment Terms',
                                  readonly=True, states={'progress': [('readonly', False)],
                                                         'payment': [('readonly', False)],
                                                         'confirm': [('readonly', False)]})

    open_document_ids = fields.One2many('tt.agent.registration.document', 'opening_document_id',
                                        'Open Registration Documents', readonly=True,
                                        states={'validate': [('readonly', False)]},
                                        help='''Checklist dokumen untuk agent, seperti seragam, banner, kartu nama, dll''')

    tac = fields.Html('Terms and Conditions', readonly=True, states={'draft': [('readonly', False)],
                                                                     'confirm': [('readonly', False)]})

    def print_agent_registration_invoice(self):
        data = {
            'ids': self.ids,
            'model': self._name
        }
        return self.env.ref('tt_agent_registration.action_report_printout_invoice').report_action(self, data=data)

    def action_send_email(self):
        template = self.env.ref('tt_agent_registration.template_mail_agent_regis')
        mail = self.env['mail.template'].browse(template.id)
        mail.send_mail(self.id)

    @api.onchange('promotion_id', 'agent_type_id')
    @api.depends('promotion_id', 'agent_type_id')
    def compute_discount(self):
        for rec in self:
            if self.agent_type_id and self.promotion_id:
                promotion_obj = self.env['tt.agent.registration.promotion'].search([('id', '=', self.promotion_id.id)], limit=1)
                rec.discount = 0
                for line in promotion_obj.agent_type_ids:
                    if line.agent_type_id == self.agent_type_id:
                        if line.discount_amount_type == 'percentage':
                            rec.discount += rec.total_fee * line.discount_amount / 100
                        else:
                            rec.discount += line.discount_amount
                rec.compute_total_fee()
            else:
                pass

    def set_parent_agent_id(self):
        for rec in self:
            if rec.agent_type_id:
                if rec.agent_type_id.id == self.env.ref('tt_base.agent_type_citra').id:
                    rec.parent_agent_id = rec.env.ref('tt_base.rodex_ho').id
                else:
                    rec.parent_agent_id = rec.env.user.agent_id
            else:
                rec.parent_agent_id = rec.env.user.agent_id
            rec.tac = rec.agent_type_id.terms_and_condition

    @api.depends('agent_type_id')
    @api.onchange('agent_type_id')
    def get_registration_fee(self):
        for rec in self:
            if rec.agent_type_id:
                promotion_obj = self.env['tt.agent.registration.promotion'].search([('default', '=', True), ('agent_type_id', '=', rec.env.user.agent_id.agent_type_id.id)], order="sequence desc", limit=1)
                rec.promotion_id = promotion_obj.id
                rec.registration_fee = rec.agent_type_id.registration_fee

    @api.depends('registration_fee', 'discount')
    @api.onchange('registration_fee', 'discount')
    def compute_total_fee(self):
        for rec in self:
            rec.total_fee = rec.registration_fee - rec.discount

    def check_address(self):
        print('Check Address')
        if not self.address_ids:
            raise UserError('Please Input an Address')

    def create_registration_documents(self):
        vals_list = []
        agent_regis_doc_ids = []
        doc_type_env = self.env['tt.document.type'].sudo().search([('agent_type_ids', '=', self.agent_type_id.id),
                                                                   ('document_type', '=', 'registration')])
        for rec in doc_type_env:
            vals = {
                'state': 'draft',
                'qty': 0,
                'receive_qty': 0,
                'document_id': rec.id
            }
            agent_regis_doc_obj = self.env['tt.agent.registration.document'].create(vals)
            agent_regis_doc_ids.append(agent_regis_doc_obj.id)
            vals_list.append(vals)
        self.registration_document_ids = [(6, 0, agent_regis_doc_ids)]
        return vals_list

    def check_registration_documents(self):
        for rec in self.registration_document_ids:
            if rec.state != 'done':
                raise UserError(_('You have to Confirmed all The Registration Documents first.'))

    def create_opening_documents(self):  # create nya jgn list of dict
        vals_list = []
        opening_doc_ids = []
        doc_type_env = self.env['tt.document.type'].sudo().search([('agent_type_ids', '=', self.agent_type_id.id),
                                                                   ('document_type', '=', 'opening')])
        for rec in doc_type_env:
            vals = {
                'state': 'draft',
                'qty': 0,
                'receive_qty': 0,
                'document_id': rec.id
            }
            opening_doc_obj = self.env['tt.agent.registration.document'].create(vals)
            opening_doc_ids.append(opening_doc_obj.id)
            vals_list.append(vals)
        self.open_document_ids = [(6, 0, opening_doc_ids)]

    def check_opening_documents(self):
        for rec in self.open_document_ids:
            if rec.state != 'done':
                raise UserError(_('You have to confirmed all the opening documents first.'))

    def set_agent_address(self):
        if self.address_ids:
            for rec in self.address_ids:
                if rec.env.user.agent_id.id is False or '':
                    rec.agent_id = False
                else:
                    rec.agent_id = rec.env.user.agent_id

    def get_all_users(self):
        query = "SELECT * FROM res_users"
        self.env.cr.execute(query)
        _logger.info(query)
        return self.env.cr.dictfetchall()

    def get_all_registration_documents_api(self):
        regis_doc_env = self.env['tt.document.type']
        regis_doc_ids = regis_doc_env.search([])

        agent_type_list = []
        agent_type_env = self.env['tt.agent.type']
        agent_type_ids = agent_type_env.search([])

        for agent_type in agent_type_ids:
            val = {
                'id': agent_type.id,
                'name': agent_type.name,
                'code': agent_type.code,
                'docs': []
            }
            agent_type_list.append(val)

        for rec in regis_doc_ids:
            if rec.document_type == 'registration':
                agent_types = []
                for agent_type in rec['agent_type_ids']:
                    agent_type_vals = {
                        'id': agent_type['id'],
                        'name': agent_type['name'],
                        'code': agent_type['code']
                    }
                    agent_types.append(agent_type_vals)

                val = {
                    'id': rec.id,
                    'document_type': rec.document_type,
                    'display_name': rec.display_name,
                    'description': rec.description
                }

                for agent_type in agent_type_list:
                    for doc_agent_type in agent_types:
                        if doc_agent_type['id'] == agent_type['id']:
                            agent_type['docs'].append(val)
        return Response().get_no_error(agent_type_list)

    def check_user_contact(self):
        users = self.get_all_users()
        if self.agent_registration_customer_ids:
            for rec in self.agent_registration_customer_ids:
                for user in users:
                    if rec.email in user.get('login'):
                        raise UserError(_('Contact with email : ' + rec.email + ' already exists. Please use another email.'))
        else:
            raise UserError(_('Please input contact information.'))

    def check_tac(self):
        if self.state == 'confirm':
            if self.tac is False or '':
                raise UserError('Terms and Conditions is Empty')

    def get_parent_citra(self, parent_agent_id):
        if parent_agent_id.parent_agent_id.agent_type_id.id == self.env.ref('tt_base.agent_type_citra').id:
            return parent_agent_id.parent_agent_id
        else:
            return self.get_parent_citra(parent_agent_id.parent_agent_id)

    def calc_commission(self):
        self.calc_ledger()
        line_obj = self.env['tt.agent.registration.promotion.agent.type'].search(
            [('promotion_id', '=', self.promotion_id.id), ('agent_type_id', '=', self.agent_type_id.id)])
        # if self.reference_id.agent_type_id.id == self.env.ref('tt_base.agent_type_ho').id:
        #     self.calc_commission_ho(line_obj)
        if self.reference_id.agent_type_id.id == self.env.ref('tt_base.agent_type_japro').id:
            self.calc_commission_japro(line_obj)
        elif self.reference_id.agent_type_id.id == self.env.ref('tt_base.agent_type_citra').id:
            self.calc_commission_citra(line_obj)

    def calc_ledger(self):
        ledger = self.env['tt.ledger']

        agent_comm_vals = ledger.prepare_vals(self._name, self.id, 'Recruit Fee : ' + self.name,
                                              'Recruit Fee : ' + self.name, datetime.now(), 2, self.currency_id.id,
                                              self.env.user.id, 0, self.total_fee)
        agent_comm_vals = ledger.prepare_vals_for_agent_regis(self, agent_comm_vals)
        agent_comm_vals.update({
            'agent_id': self.parent_agent_id.id
        })
        self.env['tt.ledger'].create(agent_comm_vals)

    def calc_commission_ho(self, line_obj):
        pass

    def calc_commission_citra(self, line_obj):
        amount_remaining = self.total_fee
        for line in line_obj.line_ids:
            if line.agent_type_id.id == self.env.ref('tt_base.agent_type_citra').id:
                ledger = self.env['tt.ledger']

                agent_comm_vals = ledger.prepare_vals(self._name, self.id, 'Recruit Comm. : ' + self.name,
                                                      'Recruit Comm. : ' + self.name, datetime.now(), 3,
                                                      self.currency_id.id, self.env.user.id, line.amount, 0)
                agent_comm_vals = ledger.prepare_vals_for_agent_regis(self, agent_comm_vals)
                agent_comm_vals.update({
                    'agent_id': self.reference_id.id
                })
                self.env['tt.ledger'].create(agent_comm_vals)
                amount_remaining -= line.amount
        # HO
        # ledger = self.env['tt.ledger']
        #
        # agent_comm_vals = ledger.prepare_vals('Recruit Comm. HO : ' + self.name, 'Recruit Comm. HO : ' +
        #                                       self.name, datetime.now(), 3, self.currency_id.id, amount_remaining,
        #                                       0)
        # agent_comm_vals = ledger.prepare_vals_for_agent_regis(self, agent_comm_vals)
        # agent_comm_vals.update({
        #     'agent_id': self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1).id
        # })
        # self.env['tt.ledger'].create(agent_comm_vals)

    def calc_commission_japro(self, line_obj):
        citra_parent_agent = self.get_parent_citra(self.parent_agent_id)
        amount_remaining = self.total_fee
        for line in line_obj.line_ids:
            if line.agent_type_id.id == self.env.ref('tt_base.agent_type_citra').id:
                ledger = self.env['tt.ledger']

                agent_comm_vals = ledger.prepare_vals(self._name, self.id, 'Recruit Comm. Parent : ' + self.name, 'Recruit Comm. Parent : ' +
                                                      self.name, datetime.now(), 3, self.currency_id.id,
                                                      self.env.user.id, line.amount, 0)
                agent_comm_vals = ledger.prepare_vals_for_agent_regis(self, agent_comm_vals)
                agent_comm_vals.update({
                    'agent_id': citra_parent_agent.id
                })
                self.env['tt.ledger'].create(agent_comm_vals)
                amount_remaining -= line.amount
            elif line.agent_type_id.id == self.env.ref('tt_base.agent_type_japro').id:
                ledger = self.env['tt.ledger']

                agent_comm_vals = ledger.prepare_vals(self._name, self.id, 'Recruit Comm. : ' + self.name,
                                                      'Recruit Comm. : ' + self.name, datetime.now(), 3,
                                                      self.env.user.id, self.currency_id.id, line.amount, 0)
                agent_comm_vals = ledger.prepare_vals_for_agent_regis(self, agent_comm_vals)
                agent_comm_vals.update({
                    'agent_id': self.reference_id.id
                })
                self.env['tt.ledger'].create(agent_comm_vals)
                amount_remaining -= line.amount
        # HO
        ledger = self.env['tt.ledger']

        agent_comm_vals = ledger.prepare_vals(self._name, self.id, 'Recruit Comm. HO : ' + self.name, 'Recruit Comm. HO : ' +
                                              self.name, datetime.now(), 3, self.env.user.id, self.currency_id.id, amount_remaining, 0)
        agent_comm_vals = ledger.prepare_vals_for_agent_regis(self, agent_comm_vals)
        agent_comm_vals.update({
            'agent_id': self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1).id
        })
        self.env['tt.ledger'].create(agent_comm_vals)

    def create_opening_balance_ledger(self, agent_id):
        ledger = self.env['tt.ledger']

        vals_credit = self.env['tt.ledger'].prepare_vals(self._name, self.id, 'Opening Balance : ' + self.name,
                                                         'Opening Balance : ' + self.name, datetime.now(), 0,
                                                         self.currency_id.id, self.env.user.id, 0, self.opening_balance)
        vals_credit = ledger.prepare_vals_for_agent_regis(self, vals_credit)
        vals_credit.update({
            'agent_id': self.parent_agent_id.id,
        })
        self.env['tt.ledger'].create(vals_credit)

        vals_debit = self.env['tt.ledger'].prepare_vals(self._name, self.id, 'Opening Balance', 'Opening Balance', datetime.now(),
                                                        0, self.currency_id.id, self.opening_balance, 0)
        vals_debit = ledger.prepare_vals_for_agent_regis(self, vals_debit)
        vals_debit.update({
            'agent_id': agent_id.id
        })
        self.env['tt.ledger'].create(vals_debit)

    def create_partner_agent(self, user_ids):
        address_ids = []
        phone_ids = []
        social_media_ids = []
        for address in self.address_ids:
            address_ids.append(address.id)
        vals = {
            'name': self.name,
            'balance': self.opening_balance,
            'agent_type_id': self.agent_type_id.id,
            'parent_agent_id': self.parent_agent_id.id,
            'reference': self.reference_id.id,
            'address_ids': [(6, 0, address_ids)],
            'logo': self.image,
            'social_media_ids': [(6, 0, social_media_ids)],
            'currency_id': self.env.user.company_id.currency_id.id,
            'user_ids': user_ids,
            'tac': self.tac
        }
        if self.agent_registration_customer_ids:
            vals.update({
                # 'website': self.contact_ids[0].website,
                'email': self.agent_registration_customer_ids[0].email,
                # 'phone_ids': self.agent_registration_customer_ids.phone_ids,
            })
        partner_obj = self.env['tt.agent'].create(vals)
        self.agent_id = partner_obj.id
        if self.social_media_ids:
            for social_media in self.social_media_ids:
                social_media.agent_id = partner_obj.id
                social_media_ids.append(social_media.id)
        self.agent_id.social_media_ids = [(6, 0, social_media_ids)]
        return partner_obj

    def create_customers_contact(self, agent_id):
        customer_id = []
        customer_parent_ids = [agent_id.customer_parent_ids[0].id]
        for rec in self:
            for con in rec.agent_registration_customer_ids:
                vals = {
                    'first_name': con['first_name'],
                    'last_name': con['last_name'],
                    'agent_id': agent_id.id,
                    'customer_parent_ids': [(6, 0, customer_parent_ids)],
                    'email': con['email'],
                    'birth_date': con['birth_date'],
                    'gender': con['gender'],
                    'marital_status': con['marital_status'],
                    'religion': con['religion'],
                }
                phone_dict = [
                    {
                        'phone_number': con['phone'],
                        'type': 'home'
                    },
                    {
                        'phone_number': con['mobile'],
                        'type': 'work'
                    }
                ]
                phone_list = []
                contact_objs = self.env['tt.customer'].create(vals)
                for phone in phone_dict:
                    vals = {
                        'phone_number': phone['phone_number'] or '0',
                        'type': phone['type']
                    }
                    phone_obj = self.env['phone.detail'].create(vals)
                    phone_id = phone_obj.id
                    phone_list.append(phone_id)
                contact_objs.update({
                    'phone_ids': [(6, 0, phone_list)]
                })
                # todo : create phone_ids untuk contact
                customer_id.append(contact_objs.id)
                con.update({
                    'customer_id': contact_objs.id,
                })
        return customer_id

    def create_agent_user(self):
        user_dict = {}
        if self.agent_type_id.user_template:
            user_dict = self.agent_type_id.user_template.read()

        user_list = []
        for rec in self:
            for con in rec.agent_registration_customer_ids:
                name = (con.first_name or '') + ' ' + (con.last_name or '')

                vals = {
                    'name': name,
                    'login': con.email,
                    'password': '123456',
                }
                if user_dict:
                    vals.update({
                        'groups_id': [(6, 0, user_dict[0]['groups_id'])]
                    })
                user_id = self.env['res.users'].create(vals)
                user_list.append(user_id.id)
        user_ids = [(6, 0, user_list)]
        return user_ids

    def action_confirm(self):
        self.check_address()
        self.set_agent_address()
        self.check_user_contact()
        self.set_parent_agent_id()
        if not self.registration_num:
            self.registration_num = self.env['ir.sequence'].next_by_code(self._name)
        if not self.registration_document_ids:
            self.create_registration_documents()
        self.state = 'confirm'

    def action_progress(self):
        self.check_tac()
        self.check_registration_documents()

        self.state = 'progress'

    def action_payment(self):
        self.state = 'payment'

    def action_validate(self):
        percentage = 0
        if not self.payment_ids:
            raise UserError('Payment Term is Empty')
        for rec in self.payment_ids:
            if rec.state not in ['paid']:
                raise UserError('Please complete all the payments.')
            else:
                percentage += rec.percentage
        if percentage >= 100:
            self.calc_commission()
            # self.partner_id = self.parent_agent_id.id
            self.create_opening_documents()
            self.state = 'validate'
        else:
            raise UserError('Please complete all the payments.')

    def action_done(self):
        try:
            self.check_opening_documents()
            user_ids = self.create_agent_user()
            agent_id = self.create_partner_agent(user_ids)
            self.create_customers_contact(agent_id)
            self.create_opening_balance_ledger(agent_id)
            self.state = 'done'
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())

    def action_cancel(self):
        self.state = 'cancel'

    def action_draft(self):
        for rec in self:
            if rec.registration_document_ids:
                for reg_doc in rec.registration_document_ids:
                    reg_doc.sudo().unlink()
            if rec.open_document_ids:
                for op_doc in rec.open_document_ids:
                    op_doc.sudo().unlink()

        self.state = 'draft'

    param_company = {
        "company_type": "individual",
        "business_license": "01/2019/04/0100-02",
        "npwp": "109358973180",
        "name": "Amrozi Tour and Travel",
    }

    param_pic = [
        {
            "birth_date": "20 Jun 2000",
            "first_name": "ivan",
            "last_name": "suryajaya",
            "email": "ivan@testing.com",
            "phone": "",
            "mobile": "08123812832",
        }
    ]

    param_address = {
        "city": 1,
        "zip": "60112",
        "address": "jl testing",
        "address2": "jl testing2"
    }

    param_regis_doc = [
        # {
        #     "data": "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAABGdBTUEAALGPC/xhBQAAAAFzUkdCAK7OHOkAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnLpRPAAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAHjtJREFUeNrt3XmcHFW99/HPOdWTTBaWhATCkpkkGNnFBa5ACPiwR5BGZF8iLSgBvC9Er/jIIyp679XHBQFZBIVmuSg8bGlANgFZRCHsQWQNkwk7YQkkZCaZqTrPH6d7pveq2TJLvu/Xa16E6erqqpo+vzrL75wCERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERlazGAfgMhgCV+Yti6ObYiYRcTOOLYiYgoR6xFiCFlBJ68T8riJ3J8Judvu2bp0sI+7PykASIX2K5obcW4zIjZ3nUwjYkNC1sXRgeF9ApZgeRHDojFfX7J8sI+3JzpfmZ4yuK2JmEPEPji2I2IDIiwOiAAHhPmfzq5/rzShe4yIC4nI2X1a2wf7XPqDAoAA0HZtszWwBSH7ErI3kduOkMkuopEQXzDC/MYBIZYPsPzTWOZjuLHxa0teHexzqKfz1emjcexCxLHGuf2I2LirwBcKffm/y4KACR2ErCTkciJ+avdrfWuwz6uvFADWcqtuaLYEfMaFZIg4kJCp3QXeQQiuUBgKBcQAFgjAWByWhRjOxnBt43FLVg32ORXrfHN6CscuOObl7/rr48BEjtgAUCsIdAIRNxPx73ZO65LBPse+UABYi626vXlrQk4g5HAiNnHFd/qiAEAEJa85fADI/5gAsHyM4SIM/9n41SUfDva5AXQunb4tEScTcSiOSeUF3DhXWejLA0FIvSBwI455ds7g9QuEL04LcEwhYKILTAcBb6aaWhJffwWAtdCqe5unE/JVQuYSMb1qIa9XCyg0BfK1ACwYHwxC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nySbwmvxKwv1dtHXggY0XDjsjIwmgF/440aSTg324+C7AXviF/fo6Re3P5YcH6hr4fAB4L5+3Otq4q9twNBeM0CqGBkBwLsHvyjJmtCYf+zY0OQft/194kc9kroOv25gPQoAw9DICQC+A+wskvWC17ISv45g3FDaOgz16q5/jNo8/Hz5vrgX/xSjJTHbjRry10QqjJwAAH45Lb+waE/muxe8hb9rnkH8dNmJDIflqHOZv+KfcXcPyUYGinXi19f7BrlMC/FpxuoDGIYs/g/dEfOTZMaVS7CfDpJ9EaME+6k+Xz6X+Tv+oZHn4wty3FzxpcC1+IeN/BYfCF6m/mdPoHJCTZJjjnvaTbGw19eg9HoswC/V9l38eoxxcx3a8QH0VOAEcplFRdep3rFYKoNiYV2D3ny/kl7P3gS2/vi+jwgp/PTZuOy3xcR/cd/Af2nqLUnl8Ovzx7kdvyZePR9Sa3WdXGYR6expwNX4BUZ3ww9rrZs/hmX43vJ/AHcAjxbNDeggnf05vt1by0q6l50ueACfNFNPiC+EcULgPApPZa7tgyrHUe16LMU/2uwG/EzHffBrI26IL7Tt+MC3ELgT/2j38kVLbwBa6nzKavysymLv4IdXx1Jftb6Kx/AjNvVqqQ6/vmFSbfilzuMWTnmVtSYI1MsGExERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERGRNeH/AxxgzqaCSy9jAAAAAElFTkSuQmCC",
        #     "content_type": "image/png",
        #     "type": "ktp"
        # },
        # {
        #     "data": "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAABGdBTUEAALGPC/xhBQAAAAFzUkdCAK7OHOkAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnLpRPAAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAHjtJREFUeNrt3XmcHFW99/HPOdWTTBaWhATCkpkkGNnFBa5ACPiwR5BGZF8iLSgBvC9Er/jIIyp679XHBQFZBIVmuSg8bGlANgFZRCHsQWQNkwk7YQkkZCaZqTrPH6d7pveq2TJLvu/Xa16E6erqqpo+vzrL75wCERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERlazGAfgMhgCV+Yti6ObYiYRcTOOLYiYgoR6xFiCFlBJ68T8riJ3J8Judvu2bp0sI+7PykASIX2K5obcW4zIjZ3nUwjYkNC1sXRgeF9ApZgeRHDojFfX7J8sI+3JzpfmZ4yuK2JmEPEPji2I2IDIiwOiAAHhPmfzq5/rzShe4yIC4nI2X1a2wf7XPqDAoAA0HZtszWwBSH7ErI3kduOkMkuopEQXzDC/MYBIZYPsPzTWOZjuLHxa0teHexzqKfz1emjcexCxLHGuf2I2LirwBcKffm/y4KACR2ErCTkciJ+avdrfWuwz6uvFADWcqtuaLYEfMaFZIg4kJCp3QXeQQiuUBgKBcQAFgjAWByWhRjOxnBt43FLVg32ORXrfHN6CscuOObl7/rr48BEjtgAUCsIdAIRNxPx73ZO65LBPse+UABYi626vXlrQk4g5HAiNnHFd/qiAEAEJa85fADI/5gAsHyM4SIM/9n41SUfDva5AXQunb4tEScTcSiOSeUF3DhXWejLA0FIvSBwI455ds7g9QuEL04LcEwhYKILTAcBb6aaWhJffwWAtdCqe5unE/JVQuYSMb1qIa9XCyg0BfK1ACwYHwxC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nySbwmvxKwv1dtHXggY0XDjsjIwmgF/440aSTg324+C7AXviF/fo6Re3P5YcH6hr4fAB4L5+3Otq4q9twNBeM0CqGBkBwLsHvyjJmtCYf+zY0OQft/194kc9kroOv25gPQoAw9DICQC+A+wskvWC17ISv45g3FDaOgz16q5/jNo8/Hz5vrgX/xSjJTHbjRry10QqjJwAAH45Lb+waE/muxe8hb9rnkH8dNmJDIflqHOZv+KfcXcPyUYGinXi19f7BrlMC/FpxuoDGIYs/g/dEfOTZMaVS7CfDpJ9EaME+6k+Xz6X+Tv+oZHn4wty3FzxpcC1+IeN/BYfCF6m/mdPoHJCTZJjjnvaTbGw19eg9HoswC/V9l38eoxxcx3a8QH0VOAEcplFRdep3rFYKoNiYV2D3ny/kl7P3gS2/vi+jwgp/PTZuOy3xcR/cd/Af2nqLUnl8Ovzx7kdvyZePR9Sa3WdXGYR6expwNX4BUZ3ww9rrZs/hmX43vJ/AHcAjxbNDeggnf05vt1by0q6l50ueACfNFNPiC+EcULgPApPZa7tgyrHUe16LMU/2uwG/EzHffBrI26IL7Tt+MC3ELgT/2j38kVLbwBa6nzKavysymLv4IdXx1Jftb6Kx/AjNvVqqQ6/vmFSbfilzuMWTnmVtSYI1MsGExERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERGRNeH/AxxgzqaCSy9jAAAAAElFTkSuQmCC",
        #     "content_type": "image/png",
        #     "type": "npwp"
        # },
        # {
        #     "data": "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAABGdBTUEAALGPC/xhBQAAAAFzUkdCAK7OHOkAAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnLpRPAAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAHjtJREFUeNrt3XmcHFW99/HPOdWTTBaWhATCkpkkGNnFBa5ACPiwR5BGZF8iLSgBvC9Er/jIIyp679XHBQFZBIVmuSg8bGlANgFZRCHsQWQNkwk7YQkkZCaZqTrPH6d7pveq2TJLvu/Xa16E6erqqpo+vzrL75wCERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERlazGAfgMhgCV+Yti6ObYiYRcTOOLYiYgoR6xFiCFlBJ68T8riJ3J8Judvu2bp0sI+7PykASIX2K5obcW4zIjZ3nUwjYkNC1sXRgeF9ApZgeRHDojFfX7J8sI+3JzpfmZ4yuK2JmEPEPji2I2IDIiwOiAAHhPmfzq5/rzShe4yIC4nI2X1a2wf7XPqDAoAA0HZtszWwBSH7ErI3kduOkMkuopEQXzDC/MYBIZYPsPzTWOZjuLHxa0teHexzqKfz1emjcexCxLHGuf2I2LirwBcKffm/y4KACR2ErCTkciJ+avdrfWuwz6uvFADWcqtuaLYEfMaFZIg4kJCp3QXeQQiuUBgKBcQAFgjAWByWhRjOxnBt43FLVg32ORXrfHN6CscuOObl7/rr48BEjtgAUCsIdAIRNxPx73ZO65LBPse+UABYi626vXlrQk4g5HAiNnHFd/qiAEAEJa85fADI/5gAsHyM4SIM/9n41SUfDva5AXQunb4tEScTcSiOSeUF3DhXWejLA0FIvSBwI455ds7g9QuEL04LcEwhYKILTAcBb6aaWhJffwWAtdCqe5unE/JVQuYSMb1qIa9XCyg0BfK1ACwYHwxC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nySbwmvxKwv1dtHXggY0XDjsjIwmgF/440aSTg324+C7AXviF/fo6Re3P5YcH6hr4fAB4L5+3Otq4q9twNBeM0CqGBkBwLsHvyjJmtCYf+zY0OQft/194kc9kroOv25gPQoAw9DICQC+A+wskvWC17ISv45g3FDaOgz16q5/jNo8/Hz5vrgX/xSjJTHbjRry10QqjJwAAH45Lb+waE/muxe8hb9rnkH8dNmJDIflqHOZv+KfcXcPyUYGinXi19f7BrlMC/FpxuoDGIYs/g/dEfOTZMaVS7CfDpJ9EaME+6k+Xz6X+Tv+oZHn4wty3FzxpcC1+IeN/BYfCF6m/mdPoHJCTZJjjnvaTbGw19eg9HoswC/V9l38eoxxcx3a8QH0VOAEcplFRdep3rFYKoNiYV2D3ny/kl7P3gS2/vi+jwgp/PTZuOy3xcR/cd/Af2nqLUnl8Ovzx7kdvyZePR9Sa3WdXGYR6expwNX4BUZ3ww9rrZs/hmX43vJ/AHcAjxbNDeggnf05vt1by0q6l50ueACfNFNPiC+EcULgPApPZa7tgyrHUe16LMU/2uwG/EzHffBrI26IL7Tt+MC3ELgT/2j38kVLbwBa6nzKavysymLv4IdXx1Jftb6Kx/AjNvVqqQ6/vmFSbfilzuMWTnmVtSYI1MsGExERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERGRNeH/AxxgzqaCSy9jAAAAAElFTkSuQmCC",
        #     "content_type": "image/png",
        #     "type": "siup"
        # },
        {
            'id': 1,
            "type": "ktp"
        },
        {
            'id': 2,
            "type": "npwp"
        },
        {
            'id': 3,
            "type": "siup"
        }
    ]

    param_other = {
        "social_media": "Telegram",
        "agent_type": "Agent JaPro"
    }

    param_context = {
        'co_uid': 7
    }

    def create_agent_registration_api(self, data, context, kwargs):  #
        company = copy.deepcopy(data['company'])  # self.param_company
        pic = copy.deepcopy(data['pic'])  # self.param_pic
        address = copy.deepcopy(data['address'])  # self.param_address
        other = copy.deepcopy(data['other'])  # self.param_other
        context = copy.deepcopy(context)  # self.param_context
        regis_doc = copy.deepcopy(data['regis_doc'])  # self.param_regis_doc
        registration_list = self.search([('name', '=', company['name'])], order='registration_date desc', limit=1)  # data['company']
        check = 0
        response = {}
        for rec in registration_list:
            response = {
                'name': rec.name,
                # 'discount': rec.discount,
                'registration_number': rec.registration_num,
                'registration_fee': int(rec.registration_fee),
                'currency': rec.currency_id.name
            }
            break
        for rec in registration_list:
            if datetime.now() <= rec.registration_date + timedelta(minutes=2):
                check = 1

        context.update({
            'co_uid': self.env.user.id
        })

        if check == 0:
            try:
                agent_type = self.env['tt.agent.type'].sudo().search([('name', '=', other.get('agent_type'))], limit=1)
                parent_agent_id = self.set_parent_agent_id_api(agent_type)
                social_media_ids = self.create_social_media_agent_regis(other)
                promotion_id = self.env['tt.agent.registration.promotion'].sudo().search([('id', '=', 10)], limit=1)
                header = self.prepare_header(company, other, agent_type)
                # contact_ids = self.prepare_contact(pic)
                agent_registration_customer_ids = self.prepare_customer(pic)
                address_ids = self.prepare_address(address)
                header.update({
                    'agent_registration_customer_ids': [(6, 0, agent_registration_customer_ids)],
                    'address_ids': [(6, 0, address_ids)],
                    'social_media_ids': [(6, 0, social_media_ids)],
                    'registration_fee': agent_type.registration_fee,
                    'registration_date': datetime.now(),
                    'promotion_id': promotion_id.id,
                    'parent_agent_id': parent_agent_id.id,
                    'tac': agent_type.terms_and_condition,
                    'create_uid': self.env.user.id
                })
                create_obj = self.create(header)
                create_obj.get_registration_fee_api()
                create_obj.compute_total_fee()
                if not create_obj.registration_num:
                    create_obj.registration_num = self.env['ir.sequence'].next_by_code(self._name)
                create_obj.input_regis_document_data(regis_doc)
                # masukkan attachment dokumen
                response = {
                    'name': create_obj.name,
                    'discount': create_obj.discount,
                    'registration_number': create_obj.registration_num,
                    'registration_fee': int(create_obj.registration_fee),
                    'currency': create_obj.currency_id.name
                }
                res = Response().get_no_error(response)
            except Exception as e:
                self.env.cr.rollback()
                _logger.error(msg=str(e) + '\n' + traceback.format_exc())
                res = Response().get_error(str(e), 500)
        else:
            res = Response().get_no_error(response)
        return res

    def prepare_header(self, company, other, agent_type):
        header = {
            'company_type': company['company_type'],
            'name': company['name'],
            'business_license': company['business_license'],
            'tax_identity_number': company['npwp'],
            'agent_type_id': agent_type.id,
        }
        return header

    def set_parent_agent_id_api(self, agent_type_id):
        if agent_type_id:
            if agent_type_id.id == self.env.ref('tt_base.agent_type_citra').id:
                parent_agent_id = self.env.ref('tt_base.rodex_ho').id
            else:
                parent_agent_id = self.env.user.agent_id
        else:
            parent_agent_id = self.env.user.agent_id
        return parent_agent_id

    def get_config_api(self):
        try:
            agent_type = []
            for rec in self.env['tt.agent.type'].search([]):
                agent_type.append({
                    'name': rec.name,
                    'is_allow_regis': rec.can_register_agent
                })
            response = {
                'agent_type': agent_type,
                'company_type': COMPANY_TYPE
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def prepare_customer(self, pic):
        customer_env = self.env['tt.agent.registration.customer']
        vals_list = []
        for rec in pic:
            vals = {
                'first_name': rec.get('first_name'),
                'last_name': rec.get('last_name'),
                'email': rec.get('email'),
                'birth_date': rec.get('birth_date'),
                'phone': rec.get('phone'),
                'mobile': rec.get('mobile'),
                'gender': rec.get('gender'),
                'marital_status': rec.get('marital_status'),
                'religion': rec.get('religion'),
            }
            customer_obj = customer_env.create(vals)
            vals_list.append(customer_obj.id)
        return vals_list

    def prepare_address(self, address):
        print(address)
        address_list = []
        address_id = self.address_ids.create({
            'zip': address.get('zip'),
            'address': address.get('address'),
            'city_id': int(address.get('city')),
            'type': 'home'
        })
        address_list.append(address_id.id)
        return address_list

    def input_regis_document_data(self, regis_doc):
        created_doc = self.create_registration_documents()
        print(str(created_doc))
        document_type_env = self.env['tt.document.type'].sudo()
        doc_ids = []
        for rec_regis_doc in regis_doc:
            upload_center_ids = []
            for doc in created_doc:
                # get doc name. ex: ktp, siup, npwp, dll.
                doc_name = str(document_type_env.search([('id', '=', doc['document_id'])], limit=1).name)
                # check jika doc name sama dengan loop rec regis doc
                if doc_name == rec_regis_doc['type'] or doc_name.lower() == rec_regis_doc['type']:
                    upload_center_ids.append(rec_regis_doc['id'])
                    break
            vals = {
                'state': 'draft',
                'qty': len(upload_center_ids),
                'receive_qty': len(upload_center_ids),
                'schedule_date': datetime.now(),
                'receive_date': datetime.now(),
                'document_id': doc['document_id'],
                'description': document_type_env.search([('id', '=', doc['document_id'])], limit=1).description,
                'document_attach_ids': [(6, 0, upload_center_ids)]
            }
            doc_obj = self.env['tt.agent.registration.document'].create(vals)
            doc_ids.append(doc_obj.id)
        self.registration_document_ids = [(6, 0, doc_ids)]
        self.state = 'confirm'

    def get_registration_fee_api(self):
        for rec in self:
            rec.registration_fee = rec.agent_type_id.registration_fee

    def create_social_media_agent_regis(self, other):
        social_media_ids = []
        if other.get('social_media'):
            social_media = self.env['social.media.detail']
            val = {
                'name': other['social_media'],
            }
            new_social_media = social_media.create(val)
            social_media_ids.append(new_social_media.id)
        return social_media_ids
