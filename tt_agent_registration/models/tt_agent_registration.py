from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError
from ...tools.api import Response
import base64
import copy
import logging
import traceback

_logger = logging.getLogger(__name__)

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
    _name = 'tt.agent.registration'
    _order = 'registration_num desc'

    name = fields.Char('Name', required=True, default='')
    image = fields.Binary('Image', store=True)
    state = fields.Selection(STATE, 'State', default='draft',
                             help='''draft = Requested
                                     confirm = HO Accepted
                                     progress = HO Processing
                                     payment = Payment
                                     validate = Validate
                                     done = Done''')
    active = fields.Boolean('Active', default=True)
    parent_agent_id = fields.Many2one('tt.agent', string="Parent Agent", Help="Agent who became Parent of This Agent")
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    partner_id = fields.Many2one('tt.agent', 'Partner id', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_type = fields.Selection(COMPANY_TYPE, 'Company Type', default='individual')
    registration_num = fields.Char('Registration No.', readonly=True)
    registration_fee = fields.Float('Registration Fee', store=True, compute='get_registration_fee')
    discount = fields.Float('Discount', readonly=True, states={'draft': [('readonly', False)],
                                                               'confirm': [('readonly', False)]})
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

    # agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', readonly=True, required=True,
    #                                 states={'draft': [('readonly', False)]})
    reference_id = fields.Many2one('tt.agent', 'Reference', readonly=False, default=lambda self: self.env.user.agent_id)
    # parent_agent_id = fields.Many2one('tt.agent', 'Parent Agent', readonly=True, store=True,
    #                                   compute='default_parent_agent_id')
    agent_level = fields.Integer('Agent Level', readonly=True)

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', readonly=True,
                                 domain=[('res_model', '=', 'tt.agent.registration')])

    contact_ids = fields.One2many('tt.customer', 'agent_registration_id', 'Contact Information')

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

    tac = fields.Text('Terms and Conditions', readonly=True, states={'draft': [('readonly', False)],
                                                                     'confirm': [('readonly', False)]})

    # def print_report_printout_invoice(self):
    #     data = {
    #         'ids': self.ids,
    #         'model': self._name
    #     }
    #     self.env.ref('printout_invoice_model').report_action(self, data=data)

    def print_agent_registration_invoice(self):
        data = {
            'ids': self.ids,
            'model': self._name
        }
        return self.env.ref('tt_agent_registration.action_report_printout_invoice').report_action(self, data=data)

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
        vals_list = []
        doc_type_env = self.env['tt.document.type'].sudo().search([('agent_type_ids', '=', self.agent_type_id.id), ('document_type', '=', 'registration')])
        for rec in doc_type_env:
            vals = {
                'state': 'draft',
                'qty': 0,
                'receive_qty': 0,
                'document_id': rec.id
            }
            vals_list.append(vals)
        self.registration_document_ids = self.env['tt.agent.registration.document'].create(vals_list)
        return vals_list

        # doc_id = self.env['tt.document.type'].sudo().search([('name', '=', 'KTP')], limit=1).id
        # vals1 = {
        #     'state': 'draft',
        #     'qty': 0,
        #     'receive_qty': 0,
        #     'document_id': doc_id
        # }
        # vals_list.append(vals1)
        #
        # if self.company_type == 'company':
        #     doc_id = self.env['tt.document.type'].sudo().search([('name', '=', 'NPWP')], limit=1).id
        #     vals = {
        #         'state': 'draft',
        #         'qty': 0,
        #         'receive_qty': 0,
        #         'document_id': doc_id
        #     }
        #     vals_list.append(vals)
        #
        # self.registration_document_ids = vals_list

    def check_registration_documents(self):
        for rec in self.registration_document_ids:
            if rec.state != 'done':
                raise UserError(_('You have to Confirmed all The Registration Documents first.'))

    def create_opening_documents(self):
        vals_list = []
        doc_type_env = self.env['tt.document.type'].sudo().search([('agent_type_ids', '=', self.agent_type_id.id), ('document_type', '=', 'opening')])
        for rec in doc_type_env:
            vals = {
                'state': 'draft',
                'qty': 0,
                'receive_qty': 0,
                'document_id': rec.id
            }
            vals_list.append(vals)
        # doc_id = self.env['tt.document.type'].sudo().search([('name', '=', 'KTP')], limit=1).id
        # vals = {
        #     'state': 'draft',
        #     'qty': 0,
        #     'receive_qty': 0,
        #     'document_id': doc_id
        # }
        self.open_document_ids = self.env['tt.agent.registration.document'].create(vals_list)

    def check_opening_documents(self):
        for rec in self.open_document_ids:
            if rec.state != 'done':
                raise UserError(_('You have to Confirmed all The Opening Documents first.'))

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
            'res_id': self.id,
            'res_model': self._name
        })
        self.env['tt.ledger'].create(agent_comm_vals)

        parent_agent_comm_vals = self.env['tt.ledger'].prepare_vals('Recruit Comm. Parent: ' + self.name,
                                                                    'Recruit Comm. Parent: ' + self.name,
                                                                    datetime.now(), 'commission', self.currency_id.id,
                                                                    parent_agent_comm, 0)
        parent_agent_comm_vals.update({
            'agent_id': self.parent_agent_id.parent_agent_id.id,
            'res_id': self.id,
            'res_model': self._name
        })
        self.env['tt.ledger'].create(parent_agent_comm_vals)

        ho_comm_vals = self.env['tt.ledger'].prepare_vals('Recruit Comm. HO: ' + self.name,
                                                          'Recruit Comm. HO: ' + self.name, datetime.now(),
                                                          'commission', self.currency_id.id, ho_comm, 0)
        ho_comm_vals.update({
            'agent_id': self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1).id,
            'res_id': self.id,
            'res_model': self._name
        })
        self.env['tt.ledger'].create(ho_comm_vals)

    def create_opening_balance_ledger(self):
        vals_credit = self.env['tt.ledger'].prepare_vals('Opening Balance : ' + self.name,
                                                         'Opening Balance : ' + self.name, datetime.now(), 'commission',
                                                         self.currency_id.id, 0, self.opening_balance)
        vals_credit.update({
            'agent_id': self.parent_agent_id.id,
            'res_id': self.id,
            'res_model': self._name
        })
        self.env['tt.ledger'].create(vals_credit)

        vals_debit = self.env['tt.ledger'].prepare_vals('Opening Balance', 'Opening Balance', datetime.now(),
                                                        'commission', self.currency_id.id, self.opening_balance, 0)
        vals_debit.update({
            'agent_id': self.partner_id.id,
            'res_id': self.id,
            'res_model': self._name
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
                # 'website': self.contact_ids[0].website,
                'email': self.contact_ids[0].email,
                'phone_ids': self.contact_ids.phone_ids,
            })
        partner_obj = self.env['tt.agent'].create(vals)
        return partner_obj

    def create_customers_contact(self):
        contact_objs = []
        for rec in self:
            print(rec.contact_ids.read())
            for con in rec.contact_ids:
                contact_vals = {
                    'name': con['name'],
                    'logo': con['logo'],
                    'logo_thumb': con['logo_thumb'],
                    'first_name': con['first_name'],
                    'last_name': con['last_name'],
                    'nickname': con['nickname'],
                    'gender': con['gender'],
                    'marital_status': con['marital_status'],
                    'religion': con['religion'],
                    'birth_date': con['birth_date'],
                    'nationality_id': con['nationality_id'],
                    'country_of_issued_id': con['country_of_issued_id'],
                    'address_ids': con['address_ids'],
                    'phone_ids': con['phone_ids'],
                    'social_media_ids': con['social_media_ids'],
                    'email': con['email'],
                    'identity_type': con['identity_type'],
                    'identity_number': con['identity_number'],
                    'passport_number': con['passport_number'],
                    'passport_expdate': con['passport_expdate'],
                    'customer_bank_detail_ids': con['customer_bank_detail_ids'],
                    'agent_id': con['agent_id'],
                    'customer_parent_ids': con['customer_parent_ids'],
                    'active': con['active'],
                    'agent_registration_id': con['agent_registration_id'].id,
                }
                contact_obj = self.env['tt.customer'].create(contact_vals)
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
        if percentage == 100:
            self.calc_commission()
            self.partner_id = self.parent_agent_id.id
            self.create_opening_documents()
            self.state = 'validate'
        else:
            raise UserError('Please complete all the payments.')

    def action_done(self):
        self.check_opening_documents()
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

    param_header = {
        "create_uid": 3,
        "company_type": "individual",
        "business_license": "",
        "npwp": "",
        "name": "suryajaya",
    }

    # param_company = {
    #     "company_type": "individual",
    #     "business_license": "",
    #     "npwp": "",
    #     "name": "suryajaya",
    #     "zip": "60112",
    #     "street": "surabaya",
    #     "street2": "",
    #     "city": "516"
    # }

    param_company = {
        "company_type": "individual",
        "business_license": "",
        "npwp": "",
        "name": "suryajaya",
        "zip": "60112",
        "street": "surabaya",
        "street2": "",
        "city": "516"
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

    param_regis_doc = {
        'ktp': [
            {
                "data": "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QAAKqNIzIAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAAHdElNRQfjBhsHEDrd3TvUAAADgklEQVRo3u2ZTWxMURiGnzvTRkv/FFEkqqWpxL+UBQthQyQWFmzKQqPSWBCijYhQxE8TQUUrlZC0kQgWNtViIfGfEBo2xEQ0TUwVDUPJYGauRTvVmTnn3nNOZyyk79nd77vf8845997vzrkWevIykzLmU0whk0gnlzB9fOUDPl7zjPt81qyorAzW0cJHbMcRpoMDzEw2vIRT9LqgY8dTKhjlWLOUlYxTgU+nmZAWPDr81JAprGlRRwSbXpa6TftBgkbw6OhkPVYCvnEw3uGEX4RvWPDouMnkGPzZIbGQDG6xnZ9JwdvYfGLtYN2muJhQaQlpwx0RarGwaEiICJTFrSTj+0cz5wVHE5TJ7ZTgJSMtDp/ONZar3J38wEeAACGyGU8xOUpnuarR1XOQViqYhTfuzELKuchX7TmI0RaXZD87yXP8AZlU8tLUQCk/HBK/sYMMpVn0UuXaMwQGvDxySGtjqtZSTqRV18BWh6R6PAbX03bC6gZy+SBJCLHRAA5gKT1PBnRIEo5QaYw/o74EWdJuvz/F+AED2yTBO0Zrr4MfMPBCGApQmHK8DbBAEjpiiD+tgbcB6oSBnzGvEeqq0cLb8gW4YISHbl0DBUSEgXmGBvxa+HcepiS8NAK08dzQwEmt7FMWUENZ3OEvHKHT0ACsYzVjFPK+08ZVY8qIRjSiEf03svhXj84i9pAbcyRECzegWqt7VRsbuC6o5gfd/v3eED9b2PTvgYcCrUJhQwO7hE3/JqD5/lJjhJ8s2e4p0zXQJPwd7jomrObrr6aOP2OIn0ZAWG9ffzjVeC93hfV+R/91pBYv/9d5KZqQWnyVpGKEheoG7hvjN0l3mS//TVKZgfqELSl3eTgqrRekSM+AzQOma+GnOW5O7BuaqnoX9LGf0UrwDHbwzaHSE9JMDNjY9LCXCY7wsVS7dJdA/PcUHQP99287W5kVt3WRxhw2084vl7PDrInFW9iYKcgbuunDSx55lCjuIVZzPP6Q7gwMZ9SKPCWmNXLl3+ETDZzDwqI2yfAQVbJViU1sGHzqbZD0MJPRzQr5ZRES4gGKeZgU/A0mOl2XHRI8gIdKeoYF76Hc7cZYQi82EeokLSeXw3w2ggc46PJ1YUD5rKLUMSObnZrfEN+wm3wVuI4Wc4JXCuh6Vqhv8ep3+gKWMZcZlJBPDjmE+U4ffrp4y2Oe0KVX7g80n8kI3NRLcgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAxOS0wNi0yN1QwNToxNjo1OCswMjowMGCy6rIAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMTktMDYtMjdUMDU6MTY6NTgrMDI6MDAR71IOAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAABJRU5ErkJggg==",
                "content_type": "image/png"
            },
            {
                "data": "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QAAKqNIzIAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAAHdElNRQfjBhsHEDrd3TvUAAADgklEQVRo3u2ZTWxMURiGnzvTRkv/FFEkqqWpxL+UBQthQyQWFmzKQqPSWBCijYhQxE8TQUUrlZC0kQgWNtViIfGfEBo2xEQ0TUwVDUPJYGauRTvVmTnn3nNOZyyk79nd77vf8845997vzrkWevIykzLmU0whk0gnlzB9fOUDPl7zjPt81qyorAzW0cJHbMcRpoMDzEw2vIRT9LqgY8dTKhjlWLOUlYxTgU+nmZAWPDr81JAprGlRRwSbXpa6TftBgkbw6OhkPVYCvnEw3uGEX4RvWPDouMnkGPzZIbGQDG6xnZ9JwdvYfGLtYN2muJhQaQlpwx0RarGwaEiICJTFrSTj+0cz5wVHE5TJ7ZTgJSMtDp/ONZar3J38wEeAACGyGU8xOUpnuarR1XOQViqYhTfuzELKuchX7TmI0RaXZD87yXP8AZlU8tLUQCk/HBK/sYMMpVn0UuXaMwQGvDxySGtjqtZSTqRV18BWh6R6PAbX03bC6gZy+SBJCLHRAA5gKT1PBnRIEo5QaYw/o74EWdJuvz/F+AED2yTBO0Zrr4MfMPBCGApQmHK8DbBAEjpiiD+tgbcB6oSBnzGvEeqq0cLb8gW4YISHbl0DBUSEgXmGBvxa+HcepiS8NAK08dzQwEmt7FMWUENZ3OEvHKHT0ACsYzVjFPK+08ZVY8qIRjSiEf03svhXj84i9pAbcyRECzegWqt7VRsbuC6o5gfd/v3eED9b2PTvgYcCrUJhQwO7hE3/JqD5/lJjhJ8s2e4p0zXQJPwd7jomrObrr6aOP2OIn0ZAWG9ffzjVeC93hfV+R/91pBYv/9d5KZqQWnyVpGKEheoG7hvjN0l3mS//TVKZgfqELSl3eTgqrRekSM+AzQOma+GnOW5O7BuaqnoX9LGf0UrwDHbwzaHSE9JMDNjY9LCXCY7wsVS7dJdA/PcUHQP99287W5kVt3WRxhw2084vl7PDrInFW9iYKcgbuunDSx55lCjuIVZzPP6Q7gwMZ9SKPCWmNXLl3+ETDZzDwqI2yfAQVbJViU1sGHzqbZD0MJPRzQr5ZRES4gGKeZgU/A0mOl2XHRI8gIdKeoYF76Hc7cZYQi82EeokLSeXw3w2ggc46PJ1YUD5rKLUMSObnZrfEN+wm3wVuI4Wc4JXCuh6Vqhv8ep3+gKWMZcZlJBPDjmE+U4ffrp4y2Oe0KVX7g80n8kI3NRLcgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAxOS0wNi0yN1QwNToxNjo1OCswMjowMGCy6rIAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMTktMDYtMjdUMDU6MTY6NTgrMDI6MDAR71IOAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAABJRU5ErkJggg==",
                "content_type": "image/png"
            }
        ],
        'siup': [
            {
                "data": "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QAAKqNIzIAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAAHdElNRQfjBhsHEDrd3TvUAAADgklEQVRo3u2ZTWxMURiGnzvTRkv/FFEkqqWpxL+UBQthQyQWFmzKQqPSWBCijYhQxE8TQUUrlZC0kQgWNtViIfGfEBo2xEQ0TUwVDUPJYGauRTvVmTnn3nNOZyyk79nd77vf8845997vzrkWevIykzLmU0whk0gnlzB9fOUDPl7zjPt81qyorAzW0cJHbMcRpoMDzEw2vIRT9LqgY8dTKhjlWLOUlYxTgU+nmZAWPDr81JAprGlRRwSbXpa6TftBgkbw6OhkPVYCvnEw3uGEX4RvWPDouMnkGPzZIbGQDG6xnZ9JwdvYfGLtYN2muJhQaQlpwx0RarGwaEiICJTFrSTj+0cz5wVHE5TJ7ZTgJSMtDp/ONZar3J38wEeAACGyGU8xOUpnuarR1XOQViqYhTfuzELKuchX7TmI0RaXZD87yXP8AZlU8tLUQCk/HBK/sYMMpVn0UuXaMwQGvDxySGtjqtZSTqRV18BWh6R6PAbX03bC6gZy+SBJCLHRAA5gKT1PBnRIEo5QaYw/o74EWdJuvz/F+AED2yTBO0Zrr4MfMPBCGApQmHK8DbBAEjpiiD+tgbcB6oSBnzGvEeqq0cLb8gW4YISHbl0DBUSEgXmGBvxa+HcepiS8NAK08dzQwEmt7FMWUENZ3OEvHKHT0ACsYzVjFPK+08ZVY8qIRjSiEf03svhXj84i9pAbcyRECzegWqt7VRsbuC6o5gfd/v3eED9b2PTvgYcCrUJhQwO7hE3/JqD5/lJjhJ8s2e4p0zXQJPwd7jomrObrr6aOP2OIn0ZAWG9ffzjVeC93hfV+R/91pBYv/9d5KZqQWnyVpGKEheoG7hvjN0l3mS//TVKZgfqELSl3eTgqrRekSM+AzQOma+GnOW5O7BuaqnoX9LGf0UrwDHbwzaHSE9JMDNjY9LCXCY7wsVS7dJdA/PcUHQP99287W5kVt3WRxhw2084vl7PDrInFW9iYKcgbuunDSx55lCjuIVZzPP6Q7gwMZ9SKPCWmNXLl3+ETDZzDwqI2yfAQVbJViU1sGHzqbZD0MJPRzQr5ZRES4gGKeZgU/A0mOl2XHRI8gIdKeoYF76Hc7cZYQi82EeokLSeXw3w2ggc46PJ1YUD5rKLUMSObnZrfEN+wm3wVuI4Wc4JXCuh6Vqhv8ep3+gKWMZcZlJBPDjmE+U4ffrp4y2Oe0KVX7g80n8kI3NRLcgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAxOS0wNi0yN1QwNToxNjo1OCswMjowMGCy6rIAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMTktMDYtMjdUMDU6MTY6NTgrMDI6MDAR71IOAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAABJRU5ErkJggg==",
                "content_type": "image/png"
            },
            {
                "data": "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QAAKqNIzIAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAAHdElNRQfjBhsHEDrd3TvUAAADgklEQVRo3u2ZTWxMURiGnzvTRkv/FFEkqqWpxL+UBQthQyQWFmzKQqPSWBCijYhQxE8TQUUrlZC0kQgWNtViIfGfEBo2xEQ0TUwVDUPJYGauRTvVmTnn3nNOZyyk79nd77vf8845997vzrkWevIykzLmU0whk0gnlzB9fOUDPl7zjPt81qyorAzW0cJHbMcRpoMDzEw2vIRT9LqgY8dTKhjlWLOUlYxTgU+nmZAWPDr81JAprGlRRwSbXpa6TftBgkbw6OhkPVYCvnEw3uGEX4RvWPDouMnkGPzZIbGQDG6xnZ9JwdvYfGLtYN2muJhQaQlpwx0RarGwaEiICJTFrSTj+0cz5wVHE5TJ7ZTgJSMtDp/ONZar3J38wEeAACGyGU8xOUpnuarR1XOQViqYhTfuzELKuchX7TmI0RaXZD87yXP8AZlU8tLUQCk/HBK/sYMMpVn0UuXaMwQGvDxySGtjqtZSTqRV18BWh6R6PAbX03bC6gZy+SBJCLHRAA5gKT1PBnRIEo5QaYw/o74EWdJuvz/F+AED2yTBO0Zrr4MfMPBCGApQmHK8DbBAEjpiiD+tgbcB6oSBnzGvEeqq0cLb8gW4YISHbl0DBUSEgXmGBvxa+HcepiS8NAK08dzQwEmt7FMWUENZ3OEvHKHT0ACsYzVjFPK+08ZVY8qIRjSiEf03svhXj84i9pAbcyRECzegWqt7VRsbuC6o5gfd/v3eED9b2PTvgYcCrUJhQwO7hE3/JqD5/lJjhJ8s2e4p0zXQJPwd7jomrObrr6aOP2OIn0ZAWG9ffzjVeC93hfV+R/91pBYv/9d5KZqQWnyVpGKEheoG7hvjN0l3mS//TVKZgfqELSl3eTgqrRekSM+AzQOma+GnOW5O7BuaqnoX9LGf0UrwDHbwzaHSE9JMDNjY9LCXCY7wsVS7dJdA/PcUHQP99287W5kVt3WRxhw2084vl7PDrInFW9iYKcgbuunDSx55lCjuIVZzPP6Q7gwMZ9SKPCWmNXLl3+ETDZzDwqI2yfAQVbJViU1sGHzqbZD0MJPRzQr5ZRES4gGKeZgU/A0mOl2XHRI8gIdKeoYF76Hc7cZYQi82EeokLSeXw3w2ggc46PJ1YUD5rKLUMSObnZrfEN+wm3wVuI4Wc4JXCuh6Vqhv8ep3+gKWMZcZlJBPDjmE+U4ffrp4y2Oe0KVX7g80n8kI3NRLcgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAxOS0wNi0yN1QwNToxNjo1OCswMjowMGCy6rIAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMTktMDYtMjdUMDU6MTY6NTgrMDI6MDAR71IOAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAABJRU5ErkJggg==",
                "content_type": "image/png"
            }
        ],
        'npwp': [
            {
                "data": "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QAAKqNIzIAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAAHdElNRQfjBhsHEDrd3TvUAAADgklEQVRo3u2ZTWxMURiGnzvTRkv/FFEkqqWpxL+UBQthQyQWFmzKQqPSWBCijYhQxE8TQUUrlZC0kQgWNtViIfGfEBo2xEQ0TUwVDUPJYGauRTvVmTnn3nNOZyyk79nd77vf8845997vzrkWevIykzLmU0whk0gnlzB9fOUDPl7zjPt81qyorAzW0cJHbMcRpoMDzEw2vIRT9LqgY8dTKhjlWLOUlYxTgU+nmZAWPDr81JAprGlRRwSbXpa6TftBgkbw6OhkPVYCvnEw3uGEX4RvWPDouMnkGPzZIbGQDG6xnZ9JwdvYfGLtYN2muJhQaQlpwx0RarGwaEiICJTFrSTj+0cz5wVHE5TJ7ZTgJSMtDp/ONZar3J38wEeAACGyGU8xOUpnuarR1XOQViqYhTfuzELKuchX7TmI0RaXZD87yXP8AZlU8tLUQCk/HBK/sYMMpVn0UuXaMwQGvDxySGtjqtZSTqRV18BWh6R6PAbX03bC6gZy+SBJCLHRAA5gKT1PBnRIEo5QaYw/o74EWdJuvz/F+AED2yTBO0Zrr4MfMPBCGApQmHK8DbBAEjpiiD+tgbcB6oSBnzGvEeqq0cLb8gW4YISHbl0DBUSEgXmGBvxa+HcepiS8NAK08dzQwEmt7FMWUENZ3OEvHKHT0ACsYzVjFPK+08ZVY8qIRjSiEf03svhXj84i9pAbcyRECzegWqt7VRsbuC6o5gfd/v3eED9b2PTvgYcCrUJhQwO7hE3/JqD5/lJjhJ8s2e4p0zXQJPwd7jomrObrr6aOP2OIn0ZAWG9ffzjVeC93hfV+R/91pBYv/9d5KZqQWnyVpGKEheoG7hvjN0l3mS//TVKZgfqELSl3eTgqrRekSM+AzQOma+GnOW5O7BuaqnoX9LGf0UrwDHbwzaHSE9JMDNjY9LCXCY7wsVS7dJdA/PcUHQP99287W5kVt3WRxhw2084vl7PDrInFW9iYKcgbuunDSx55lCjuIVZzPP6Q7gwMZ9SKPCWmNXLl3+ETDZzDwqI2yfAQVbJViU1sGHzqbZD0MJPRzQr5ZRES4gGKeZgU/A0mOl2XHRI8gIdKeoYF76Hc7cZYQi82EeokLSeXw3w2ggc46PJ1YUD5rKLUMSObnZrfEN+wm3wVuI4Wc4JXCuh6Vqhv8ep3+gKWMZcZlJBPDjmE+U4ffrp4y2Oe0KVX7g80n8kI3NRLcgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAxOS0wNi0yN1QwNToxNjo1OCswMjowMGCy6rIAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMTktMDYtMjdUMDU6MTY6NTgrMDI6MDAR71IOAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAABJRU5ErkJggg==",
                "content_type": "image/png"
            },
            {
                "data": "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QAAKqNIzIAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAAHdElNRQfjBhsHEDrd3TvUAAADgklEQVRo3u2ZTWxMURiGnzvTRkv/FFEkqqWpxL+UBQthQyQWFmzKQqPSWBCijYhQxE8TQUUrlZC0kQgWNtViIfGfEBo2xEQ0TUwVDUPJYGauRTvVmTnn3nNOZyyk79nd77vf8845997vzrkWevIykzLmU0whk0gnlzB9fOUDPl7zjPt81qyorAzW0cJHbMcRpoMDzEw2vIRT9LqgY8dTKhjlWLOUlYxTgU+nmZAWPDr81JAprGlRRwSbXpa6TftBgkbw6OhkPVYCvnEw3uGEX4RvWPDouMnkGPzZIbGQDG6xnZ9JwdvYfGLtYN2muJhQaQlpwx0RarGwaEiICJTFrSTj+0cz5wVHE5TJ7ZTgJSMtDp/ONZar3J38wEeAACGyGU8xOUpnuarR1XOQViqYhTfuzELKuchX7TmI0RaXZD87yXP8AZlU8tLUQCk/HBK/sYMMpVn0UuXaMwQGvDxySGtjqtZSTqRV18BWh6R6PAbX03bC6gZy+SBJCLHRAA5gKT1PBnRIEo5QaYw/o74EWdJuvz/F+AED2yTBO0Zrr4MfMPBCGApQmHK8DbBAEjpiiD+tgbcB6oSBnzGvEeqq0cLb8gW4YISHbl0DBUSEgXmGBvxa+HcepiS8NAK08dzQwEmt7FMWUENZ3OEvHKHT0ACsYzVjFPK+08ZVY8qIRjSiEf03svhXj84i9pAbcyRECzegWqt7VRsbuC6o5gfd/v3eED9b2PTvgYcCrUJhQwO7hE3/JqD5/lJjhJ8s2e4p0zXQJPwd7jomrObrr6aOP2OIn0ZAWG9ffzjVeC93hfV+R/91pBYv/9d5KZqQWnyVpGKEheoG7hvjN0l3mS//TVKZgfqELSl3eTgqrRekSM+AzQOma+GnOW5O7BuaqnoX9LGf0UrwDHbwzaHSE9JMDNjY9LCXCY7wsVS7dJdA/PcUHQP99287W5kVt3WRxhw2084vl7PDrInFW9iYKcgbuunDSx55lCjuIVZzPP6Q7gwMZ9SKPCWmNXLl3+ETDZzDwqI2yfAQVbJViU1sGHzqbZD0MJPRzQr5ZRES4gGKeZgU/A0mOl2XHRI8gIdKeoYF76Hc7cZYQi82EeokLSeXw3w2ggc46PJ1YUD5rKLUMSObnZrfEN+wm3wVuI4Wc4JXCuh6Vqhv8ep3+gKWMZcZlJBPDjmE+U4ffrp4y2Oe0KVX7g80n8kI3NRLcgAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAxOS0wNi0yN1QwNToxNjo1OCswMjowMGCy6rIAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMTktMDYtMjdUMDU6MTY6NTgrMDI6MDAR71IOAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAABJRU5ErkJggg==",
                "content_type": "image/png"
            }
        ],
    }

    param_other = {
        "social_media": 0,
        "agent_type": "Agent Citra"
    }

    param_context = {
        'co_uid': 7
    }

    def create_agent_registration_api(self):
        company = copy.deepcopy(self.param_company)
        pic = copy.deepcopy(self.param_pic)
        other = copy.deepcopy(self.param_other)
        context = copy.deepcopy(self.param_context)
        regis_doc = copy.deepcopy(self.param_regis_doc)

        context.update({
            'co_uid': self.env.user.id
        })

        try:
            agent_type = self.env['tt.agent.type'].sudo().search([('name', '=', other.get('agent_type'))], limit=1)
            header = self.prepare_header(company, other, agent_type)
            contact_ids = self.prepare_contact(pic)
            header.update({
                'contact_ids': [(6, 0, contact_ids)],
                'registration_fee': agent_type.registration_fee,
                'registration_date': datetime.now(),
                'create_uid': self.env.user.id
            })
            create_obj = self.create(header)
            create_obj.get_registration_fee()
            create_obj.compute_total_fee()
            if not create_obj.registration_num:
                create_obj.registration_num = self.env['ir.sequence'].next_by_code('agent.registration')
            create_obj.input_regis_document_data(regis_doc)
            # masukkan attachment dokumen
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e)
            }

    def prepare_header(self, company, other, agent_type):
        header = {
            'company_type': company['company_type'],
            'name': company['name'],
            'business_license': company['business_license'],
            'tax_identity_number': company['npwp'],
            'agent_type_id': agent_type.id,
        }
        return header

    def get_config_api(self):
        try:
            agent_type = []
            for rec in self.env['tt.agent.type'].search([]):
                agent_type.append({
                    'name': rec.name,
                    'is_allow_regis': rec.is_allow_regis
                })
            response = agent_type
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def prepare_contact(self, pic):
        contact_env = self.env['tt.customer'].sudo()
        vals_list = []

        for rec in pic:
            vals = {
                'birth_date': rec.get('birth_date'),
                'first_name': rec.get('first_name'),
                'last_name': rec.get('last_name'),
                'email': rec.get('email'),
                # 'phone': rec.get('phone'),
            }
            contact_obj = contact_env.create(vals)
            contact_obj.update({
                'phone_ids': contact_obj.phone_ids.create({
                    'phone_number': rec.get('mobile', rec['mobile']),
                    'type': 'work'
                }),
            })
            vals_list.append(contact_obj.id)
        return vals_list

    def prepare_address(self, company):
        address_list = []
        address_id = self.address_ids.create({
            'zip': company.get('zip'),
            'address': company.get('street'),
            'city': company.get('city'),
            'type': 'home'
        })
        address_list.append(address_id.id)
        return address_list

    def input_regis_document_data(self, regis_doc):
        created_doc = self.create_registration_documents()
        document_type_env = self.env['tt.document.type'].sudo()
        doc_list = []
        for rec_regis_doc in regis_doc:
            for doc in created_doc:
                doc_name = str(document_type_env.search([('id', '=', doc['document_id'])], limit=1).name)
                if str(rec_regis_doc) == doc_name or str(rec_regis_doc) == doc_name.lower():
                    # progress now : update doc done, minus attachment belum masuk
                    attachment_list = []
                    for rec_regis_doc2 in regis_doc[rec_regis_doc]:
                        # print('Regis Doc 2 : ' + str(rec_regis_doc2))
                        if rec_regis_doc2.get('data') and rec_regis_doc2.get('content_type'):
                            attachment_value = {
                                'name': str(rec_regis_doc) + '.png',
                                'datas': rec_regis_doc2.get('data'),
                                'datas_fname': str(rec_regis_doc) + '.png',
                                'res_model': self._name,
                                'res_id': self.id,
                                'type': 'binary',
                                'mimetype': rec_regis_doc2.get('content_type'),
                            }
                            attachment_obj = self.env['ir.attachment'].sudo().create(attachment_value)
                            attachment_list.append(attachment_obj.id)

                    # self.env['ir.attachment'].sudo().create(attachment_value)
                    # print('Doc : ' + str(doc))
                    vals = {
                        'state': 'draft',
                        'qty': len(attachment_list),
                        'receive_qty': len(attachment_list),
                        'schedule_date': datetime.now(),
                        'receive_date': datetime.now(),
                        'document_id': doc['document_id'],
                        'description': document_type_env.search([('id', '=', doc['document_id'])], limit=1).description,
                        'attachment_ids': [(6, 0, attachment_list)]
                    }
                    doc_list.append(vals)
                    break
        print(doc_list)
        self.registration_document_ids = self.env['tt.agent.registration.document'].create(doc_list)
        self.state = 'confirm'
        # self.state = 'confirm'
