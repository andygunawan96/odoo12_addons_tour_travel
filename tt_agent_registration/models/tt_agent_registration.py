from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError

COMPANY_TYPE = [
    ('individual', 'Individual'),
    ('company', 'Company')
]

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('progress', 'Progress'),
    ('payment', 'Payment'),
    ('validate', 'Validate'),
    ('done', 'Done'),
    ('cancel', 'Cancel')
]


class AgentRegistration(models.Model):
    _inherit = 'tt.agent'
    _name = 'tt.agent.registration'

    image = fields.Binary('Image')
    state = fields.Selection(STATE, 'State', default='draft')
    active = fields.Boolean('Active', default=True)
    partner_id = fields.Many2one('tt.agent', 'Partner id', readonly=True)
    company_type = fields.Selection(COMPANY_TYPE, 'Company Type', default='individual')
    registration_num = fields.Char('Registration Number', readonly=True)
    registration_fee = fields.Float('Registration Fee', store=True, compute='get_registration_fee')
    discount = fields.Float('Discount', readonly=True, states={'draft': [('readonly', False)]})
    opening_balance = fields.Float('Opening Balance', readonly=True, states={'draft': [('readonly', False)],
                                                                             'confirm': [('readonly', False)]})
    total_fee = fields.Monetary('Total Fee', store=True, compute='compute_total_fee')
    registration_date = fields.Date('Registration Date', required=True, readonly=True,
                                    states={'draft': [('readonly', False)]})
    expired_date = fields.Date('Expired Date', readonly=True, states={'draft': [('readonly', False)]})

    business_license = fields.Char('Business License')
    tax_identity_number = fields.Char('NPWP')

    address_ids = fields.One2many('address.detail', 'agent_registration_id', string='Addresses')
    social_media_ids = fields.One2many('social.media.detail', 'agent_registration_id', 'Social Media')

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', readonly=True, required=True,
                                    states={'draft': [('readonly', False)]})
    reference_id = fields.Many2one('tt.agent', 'Reference', readonly=True, default=lambda self: self.env.user.agent_id)
    parent_agent_id = fields.Many2one('tt.agent', 'Parent Agent', readonly=True, store=True,
                                      compute='default_parent_agent_id')
    agent_level = fields.Integer('Agent Level', readonly=True)

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', readonly=True)

    contact_ids = fields.One2many('tt.customer', 'agent_id', 'Contact Information')

    registration_document_ids = fields.One2many('tt.agent.registration.document', 'registration_document_id',
                                                'Agent Registration Documents', readonly=True,
                                                states={'confirm': [('readonly', False)]})

    payment_ids = fields.One2many('tt.agent.registration.payment', 'agent_registration_id', 'Payment Terms',
                                  readonly=True, states={'progress': [('readonly', False)],
                                                         'payment': [('readonly', False)],
                                                         'confirm': [('readonly', False)]})

    open_document_ids = fields.One2many('tt.agent.registration.document', 'opening_document_id',
                                        'Open Registration Documents', readonly=True,
                                        states={'validate': [('readonly', False)]})

    def print_report_printout_invoice(self):
        data = {
            'ids': self.ids,
            'model': self._name
        }
        self.env.ref('printout_invoice_model').report_action(self, data=data)

    @api.onchange('agent_type_id')
    @api.depends('agent_type_id')
    def default_parent_agent_id(self):
        if self.agent_type_id:
            if self.agent_type_id.name == 'Citra':
                self.parent_agent_id = self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1)
            else:
                self.parent_agent_id = self.env.user.agent_id
        else:
            self.parent_agent_id = self.env.user.agent_id

    @api.depends('agent_type_id')
    @api.onchange('agent_type_id')
    def get_registration_fee(self):
        for rec in self:
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
        doc_id = self.env['tt.document.type'].sudo().search([('name', '=', 'KTP')], limit=1).id
        vals = {
            'state': 'draft',
            'qty': 0,
            'receive_qty': 0,
            'document_id': doc_id
        }
        self.registration_document_ids = self.env['tt.agent.registration.document'].create(vals)

    def create_opening_documents(self):
        doc_id = self.env['tt.document.type'].sudo().search([('name', '=', 'KTP')], limit=1).id
        vals = {
            'state': 'draft',
            'qty': 0,
            'receive_qty': 0,
            'document_id': doc_id
        }
        self.open_document_ids = self.env['tt.agent.registration.document'].create(vals)

    def set_agent_address(self):
        print('Set Agent Address')
        print(self.env.user.agent_id.id)
        if self.address_ids:
            for rec in self:
                if rec.env.user.agent_id.id is False or '':
                    rec.address_ids.agent_id = False
                else:
                    rec.address_ids.agent_id = rec.env.user.agent_id

    def check_tac(self):
        if self.state == 'confirm':
            if self.tac is False or '':
                raise UserError('Terms and Conditions is Empty')

    def calc_commission(self):
        # Hitung dulu semua komisi, lalu masukkan ke dalam ledger
        agent_comm, parent_agent_comm, ho_comm = self.agent_type_id.calc_recruitment_commission(self.parent_agent_id.agent_type_id, self.total_fee)

        agent_comm_vals = self.env['tt.ledger'].prepare_vals('Recruit Comm. : ' + self.name,
                                                             'Recruit Comm. : ' + self.name, datetime.now(),
                                                             'commission', self.currency_id.id, agent_comm, 0)
        agent_comm_vals.update({
            'agent_id': self.parent_agent_id.id,
            'res_id': self.id
        })
        self.env['tt.ledger'].create(agent_comm_vals)

        parent_agent_comm_vals = self.env['tt.ledger'].prepare_vals('Recruit Comm. Parent: ' + self.name,
                                                                    'Recruit Comm. Parent: ' + self.name,
                                                                    datetime.now(), 'commission', self.currency_id.id,
                                                                    parent_agent_comm, 0)
        parent_agent_comm_vals.update({
            'agent_id': self.parent_agent_id.parent_agent_id.id,
            'res_id': self.id
        })
        self.env['tt.ledger'].create(parent_agent_comm_vals)

        ho_comm_vals = self.env['tt.ledger'].prepare_vals('Recruit Comm. HO: ' + self.name,
                                                          'Recruit Comm. HO: ' + self.name, datetime.now(),
                                                          'commission', self.currency_id.id, ho_comm, 0)
        ho_comm_vals.update({
            'agent_id': self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1).id,
            'res_id': self.id
        })
        self.env['tt.ledger'].create(ho_comm_vals)

    def create_opening_balance_ledger(self):
        vals_credit = self.env['tt.ledger'].prepare_vals('Opening Balance : ' + self.name,
                                                         'Opening Balance : ' + self.name, datetime.now(), 'commission',
                                                         self.currency_id.id, 0, self.opening_balance)
        vals_credit.update({
            'agent_id': self.parent_agent_id.id,
            'res_id': self.id
        })
        self.env['tt.ledger'].create(vals_credit)

        vals_debit = self.env['tt.ledger'].prepare_vals('Opening Balance', 'Opening Balance', datetime.now(),
                                                        'commission', self.currency_id.id, self.opening_balance, 0)
        vals_debit.update({
            'agent_id': self.partner_id.id,
            'res_id': self.id
        })
        self.env['tt.ledger'].create(vals_debit)

    def create_partner_agent(self):
        vals = {
            'name': self.name,
            'balance': self.opening_balance,
            'agent_type_id': self.agent_type_id.id,
            'parent_agent_id': self.parent_agent_id.id,
            'address_ids': self.address_ids,
            'logo': self.image,
            'social_media_ids': self.social_media_ids,
            'currency_id': self.env.user.company_id.currency_id.id,
            'user_ids': '',
            'tac': self.tac
        }
        if self.contact_ids:
            vals.update({
                'website': self.contact_ids[0].website,
                'email': self.contact_ids[0].email,
                'phone_ids': self.contact_ids.phone_ids,
            })
        partner_obj = self.env['tt.agent'].create(vals)
        return partner_obj

    def create_customers_contact(self):
        contact_objs = []
        for rec in self:
            contact_obj = self.env['tt.customer'].create(rec.contact_ids.read())
            contact_objs.append(contact_obj)
        # contact_obj = self.env['tt.customer'].create(self.contact_ids)
        return contact_objs

    def action_confirm(self):
        # self.check_address()
        # self.set_agent_address()
        if not self.registration_num:
            self.registration_num = self.env['ir.sequence'].next_by_code('agent.registration')
        if not self.registration_document_ids:
            self.create_registration_documents()
        self.state = 'confirm'

    def action_progress(self):
        self.check_tac()
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
        if percentage == 100:
            self.calc_commission()
            self.partner_id = self.parent_agent_id.id
            self.create_opening_documents()
            self.state = 'validate'
        else:
            raise UserError('Please complete all the payments.')

    def action_done(self):
        self.partner_id = self.create_partner_agent()
        if self.contact_ids:
            self.create_customers_contact()
        self.create_opening_balance_ledger()
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def action_draft(self):
        # self.create_uid = False
        # self.create_date = False
        # self.cancel_date = False
        # self.cancel_uid = False

        # self.agent_type_id.sudo().unlink()
        # self.parent_agent_id.sudo().unlink()
        # self.reference_id.sudo().unlink()
        # self.partner_id.sudo().unlink()
        #
        # self.registration_num = False
        # self.registration_fee = False
        # self.registration_date = False
        # self.total_fee = False
        # self.discount = False
        # self.opening_balance = False
        #
        # self.ledger_ids.sudo().unlink()
        # self.address_ids.sudo().unlink()
        # self.contact_ids.sudo().unlink()
        # self.registration_document_ids.sudo().unlink()
        # self.open_document_ids.sudo().unlink()
        # self.payment_ids.sudo().unlink()
        if self.registration_document_ids:
            for rec in self:
                rec.registration_document_ids.active = False
        if self.open_document_ids:
            for rec in self:
                rec.open_document_ids.active = False

        self.state = 'draft'
