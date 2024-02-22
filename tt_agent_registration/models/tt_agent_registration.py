from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError
from ...tools.api import Response
import base64
import copy
import logging,pytz
import traceback
from ...tools.api import Response
from ...tools.ERR import RequestException

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
    _description = 'Agent Registration'
    _rec_name = 'registration_num'
    _order = 'registration_num desc'

    name = fields.Char('Name', default='', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    image = fields.Binary('Image', store=True)
    state = fields.Selection(STATE, 'State', default='draft',
                             help='''draft = Draft status is used for Agent to make Agent Registration request.
                                     confirm = Confirm status is used for HO to confirm and process the request.
                                     surveying = Surveying status is used for HO to survey the location (if needed)
                                     payment = Payment status is used for HO to make the payment progress
                                     validate = Validate status is used for HO to validate the request
                                     done = Done status means the request has been done''')
    active = fields.Boolean('Active', default=True)
    parent_agent_id = fields.Many2one('tt.agent', string="Parent Agent", Help="Agent who became Parent of This Agent",
                                      readonly=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True, readonly=True,
                                    states={'draft': [('readonly', False)]})

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True, default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent ID', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_type = fields.Selection(COMPANY_TYPE, 'Company Type', default='individual', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    registration_num = fields.Char('Registration No.', readonly=True)
    registration_fee = fields.Float('Registration Fee', store=True, compute='get_registration_fee')
    # promotion_id required supaya agent yang merekrut bisa dapat komisi

    def get_promotion_ids(self):
        promotions_list = []
        promotion_objs = self.env['tt.agent.registration.promotion'].search([('agent_type_id', '=', self.reference_id.agent_type_id.id)])
        for rec in promotion_objs:
            if rec.start_date <= date.today() <= rec.end_date:
                promotions_list.append(rec.id)
        if not promotions_list:
            search_params = [('default', '=', True)]
            ho_obj = self.env.user.agent_id.ho_id
            agent_type_obj = ho_obj and ho_obj.agent_type_id or False
            if agent_type_obj:
                search_params.append(('agent_type_id', '=', agent_type_obj.id))
            promotion_obj = self.env['tt.agent.registration.promotion'].search(search_params, limit=1)
            if promotion_obj:
                promotions_list.append(promotion_obj.id)
        return [('id', 'in', promotions_list)]

    promotion_id = fields.Many2one('tt.agent.registration.promotion', 'Promotion', readonly=True, required=False,
                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                   domain=[('id', '=', -1)])
    dummy_promotion = fields.Boolean('Generate Promotions', default=False, help="Generate Promotions List")
    discount = fields.Float('Discount', readonly=True, compute='compute_discount')
    opening_balance = fields.Float('Opening Balance', readonly=True, states={'draft': [('readonly', False)],
                                                                             'confirm': [('readonly', False)]})
    total_fee = fields.Monetary('Total Fee', compute='compute_total_fee')
    registration_date = fields.Datetime('Registration Date', required=True, readonly=True,
                                        states={'draft': [('readonly', False)]})
    expired_date = fields.Date('Expired Date', readonly=True, states={'draft': [('readonly', False)]})

    business_license = fields.Char('Business License')
    tax_identity_number = fields.Char('NPWP')

    reference_id = fields.Many2one('tt.agent', 'Reference', readonly=True, default=lambda self: self.env.user.agent_id)
    agent_level = fields.Integer('Agent Level', readonly=True)

    issued_uid = fields.Many2one('res.users', 'Issued by', readonly=True)
    issued_date = fields.Datetime('Issued Date', readonly=True)

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', readonly=True,
                                 domain=[('res_model', '=', 'tt.agent.registration')])

    agent_registration_customer_ids = fields.One2many('tt.agent.registration.customer', 'agent_registration_id',
                                                      'Agent Registration Contact')
    address_ids = fields.One2many('tt.agent.registration.address', 'agent_registration_id', string='Addresses')
    social_media_ids = fields.One2many('social.media.detail', 'agent_registration_id', 'Social Media')

    registration_document_ids = fields.One2many('tt.agent.registration.document', 'registration_document_id',
                                                'Agent Registration Documents', readonly=True,
                                                states={'confirm': [('readonly', False)]},
                                                help='''Dokumen yang perlu dilengkapi saat pendaftaran, seperti KTP, NPWP, dll''')

    payment_ids = fields.One2many('tt.agent.registration.payment', 'agent_registration_id', 'Payment Terms',
                                  readonly=True, states={'payment': [('readonly', False)]})

    open_document_ids = fields.One2many('tt.agent.registration.document', 'opening_document_id',
                                        'Open Registration Documents', readonly=True,
                                        states={'validate': [('readonly', False)]},
                                        help='''Checklist dokumen untuk agent, seperti seragam, banner, kartu nama, dll''')

    tac = fields.Html('Terms and Conditions', readonly=True, states={'draft': [('readonly', False)],
                                                                     'confirm': [('readonly', False)]})

    @api.multi
    def write(self, vals_list):
        vals_list.update({
            'dummy_promotion': False
        })
        return super(AgentRegistration, self).write(vals_list)

    @api.depends('parent_agent_id', 'dummy_promotion')
    @api.onchange('parent_agent_id', 'dummy_promotion')
    def _onchange_domain_promotion(self):
        return {'domain': {
            'promotion_id': self.get_promotion_ids()
        }}

    def print_agent_registration_invoice(self):
        data = {
            'ids': self.ids,
            'model': self._name
        }
        return self.env.ref('tt_agent_registration.action_report_printout_invoice').report_action(self, data=data)

    def action_send_email(self):
        if not self.env.user.has_group('tt_base.group_agent_registration_master_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 33')
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

    @staticmethod
    def reg_upline_contains(agent_type_id, target_agent_type_id):
        for upline in agent_type_id.registration_upline_ids:
            if upline.code == target_agent_type_id.code:
                return True
        return False

    def set_parent_agent_id(self):
        for rec in self:
            if rec.agent_type_id:
                # Set parent agent berdasarkan registration upline di agent type
                if not rec.agent_type_id.registration_upline_ids:
                    """ Jika registration upline ids kosong, langsung set ke HO yang lagi login """
                    rec.parent_agent_id = rec.env.user.ho_id.id
                else:
                    if rec.reg_upline_contains(rec.agent_type_id, rec.env.user.agent_id.agent_type_id):
                        rec.parent_agent_id = rec.env.user.agent_id.id
                    else:
                        ho_obj = rec.env.user.agent_id.ho_id
                        agent_type_obj = ho_obj and ho_obj.agent_type_id or False
                        if rec.reg_upline_contains(rec.agent_type_id, agent_type_obj):
                            rec.parent_agent_id = rec.env.user.ho_id.id
                        else:
                            pass
            else:
                rec.parent_agent_id = rec.env.user.agent_id
            rec.tac = rec.agent_type_id.terms_and_condition

    @api.depends('agent_type_id')
    @api.onchange('agent_type_id')
    def get_registration_fee(self):
        for rec in self:
            if rec.agent_type_id:
                if self.promotion_id:
                    promotion_obj = self.env['tt.agent.registration.promotion'].search([('default', '=', True), ('agent_type_id', '=', rec.env.user.agent_id.agent_type_id.id)], order="sequence desc", limit=1)
                    rec.promotion_id = promotion_obj.id
                    rec.registration_fee = rec.agent_type_id.registration_fee
                else:
                    rec.registration_fee = rec.agent_type_id.registration_fee

    @api.depends('registration_fee', 'discount')
    @api.onchange('registration_fee', 'discount')
    def compute_total_fee(self):
        for rec in self:
            rec.total_fee = rec.registration_fee - rec.discount

    def check_address(self):
        if not self.address_ids:
            raise UserError('Please Input an Address')

    def create_registration_documents(self):
        for rec in self:
            vals_list = []
            agent_regis_doc_ids = []
            doc_type_env = rec.env['tt.document.type'].sudo().search([('agent_type_ids', '=', rec.agent_type_id.id),
                                                                       ('document_type', '=', 'registration')])
            for rec in doc_type_env:
                vals = {
                    'state': 'draft',
                    'qty': 0,
                    'receive_qty': 0,
                    'document_id': rec.id
                }
                agent_regis_doc_obj = self.env['tt.agent.registration.document'].sudo().create(vals)
                agent_regis_doc_ids.append(agent_regis_doc_obj.id)
                vals_list.append(vals)
            rec.sudo().registration_document_ids = [(6, 0, agent_regis_doc_ids)]
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

    def get_promotions_api(self, context):
        _logger.info('Mulai get promotions api')
        res = []
        try:
            agent_type_id = context['co_agent_type_id']
            promotion_env = self.env['tt.agent.registration.promotion']
            promotion_ids = promotion_env.search([('start_date', '<=', date.today()), ('end_date', '>=', date.today()), ('agent_type_id', '=', agent_type_id),('default','=',True)])

            for promotion in promotion_ids:
                val = {
                    'id': promotion.id,
                    'name': promotion.name,
                    'agent_type': promotion.agent_type_id.name,
                    'start_date': promotion.start_date.strftime("%Y-%m-%d"),
                    'end_date': promotion.end_date.strftime("%Y-%m-%d"),
                    'default_commission': promotion.default,
                    'description': promotion.description,
                    'commission': []
                }
                _logger.info('Mulai promotion agent type ids')
                for commission in promotion.agent_type_ids:
                    comm = {
                        'recruited': commission.agent_type_id.name,
                        # 'currency_id': self.env.user.company_id.currency_id.name,
                        'currency': commission.currency_id.name,
                        'registration_fee': commission.agent_type_id.registration_fee,
                        'discount_type': commission.discount_amount_type,
                        'discount_amount': commission.discount_amount,
                        'lines': []
                    }
                    _logger.info('Mulai promotion line ids')
                    for commission_line in commission.line_ids:
                        line = {
                            'agent_type_id': commission_line.agent_type_id.id,
                            'agent_type_name': commission_line.agent_type_id.name,
                            'amount': commission_line.amount
                        }
                        comm['lines'].append(line)
                    _logger.info('Proses promotion line ids selesai')
                    val['commission'].append(comm)

                _logger.info('Proses promotion agent type ids selesai')
                res.append(val)

            _logger.info('Melakukan pengecekan jika response kosong')
            if not res:
                _logger.info('Response kosong. Input Normal Price.')
                # Jika agent type tidak memiliki promotion, maka hanya return Normal Price (tanpa komisi)
                search_params = [('default', '=', True)]
                if context.get('co_ho_id'):
                    ho_obj = self.env['tt.agent'].browse(int(context['co_ho_id']))
                    if ho_obj.agent_type_id:
                        search_params.append(('agent_type_id', '=', ho_obj.agent_type_id.id))
                normal_price_promotion = promotion_env.search(search_params, limit=1)

                val = {
                    'id': normal_price_promotion.id,
                    'name': normal_price_promotion.name,
                    'agent_type': normal_price_promotion.agent_type_id.name,
                    'start_date': normal_price_promotion.start_date.strftime("%Y-%m-%d"),
                    'end_date': normal_price_promotion.end_date.strftime("%Y-%m-%d"),
                    'default_commission': normal_price_promotion.default,
                    'description': normal_price_promotion.description,
                    'commission': []
                }
                res.append(val)
            res = Response().get_no_error(res)
            return res
        except Exception as e:
            res = Response().get_error(str(e), 500)
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return res

    def get_all_registration_documents_api(self, context):
        search_params = []
        if context.get('co_ho_id'):
            search_params.append(('ho_id', '=', int(context['co_ho_id'])))
        agent_type_ids = self.env['tt.agent.type'].search(search_params)

        agent_type_list = []
        for agent_type in agent_type_ids:
            agent_type_list.append({
                'id': agent_type.id,
                'name': agent_type.name,
                'code': agent_type.code,
                'docs': []
            })

        regis_doc_ids = self.env['tt.document.type'].search([])
        for rec in regis_doc_ids:
            if rec.document_type == 'registration':
                val = {
                    'id': rec.id,
                    'document_type': rec.document_type,
                    'display_name': rec.display_name,
                    'description': rec.description
                }
                for agent_type in agent_type_list:
                    for doc_agent_type in rec.agent_type_ids:
                        if doc_agent_type.id == agent_type['id']:
                            agent_type['docs'].append(val)
        return Response().get_no_error(agent_type_list)

    def check_user_contact(self):
        users = self.get_all_users()
        users_email = []
        if self.agent_registration_customer_ids:
            for rec in self.agent_registration_customer_ids:
                if rec.email not in users_email:
                    users_email.append(rec.email)
                    for user in users:
                        if rec.email in user.get('login'):
                            raise UserError(_('Contact with email : ' + rec.email + ' already exists. Please use another email.'))
                else:
                    raise UserError(_('Two or more users cannot use same email. Please use another email.'))
        else:
            raise UserError(_('Please input contact information.'))

    def check_tac(self):
        if self.state == 'confirm':
            if self.tac is False or '':
                raise UserError('Terms and Conditions is Empty')

    def calc_commission(self):
        ledger = self.env['tt.ledger']
        self.calc_ledger()

        comm_left = self.total_fee
        promotion_obj = self.env['tt.agent.registration.promotion'].search([('id', '=', self.promotion_id.id)]
                                                                           , limit=1)
        comm = promotion_obj.get_commission(self.registration_fee, self.agent_type_id, self.reference_id, self.promotion_id)
        for rec in comm:
            if rec['agent_type_id'] == self.reference_id.agent_type_id.id:
                # Ledger untuk komisi reference agent
                ledger.create_ledger_vanilla(
                    self._name,
                    self.id,
                    'Recruit Comm. : ' + self.name,
                    'Recruit Comm. : ' + self.name,
                    3,
                    self.currency_id.id,
                    self.env.user.id,
                    self.reference_id.id,
                    False,
                    rec['amount'],
                    0,
                    'Ledger for ' + self.name,
                )
            else:
                # Komisi etc
                agent_obj = self.env['tt.agent'].search([('id', '=', rec['agent_id'])])
                ledger.create_ledger_vanilla(
                    self._name,
                    self.id,
                    'Recruit Comm. Parent : ' + self.name,
                    'Recruit Comm. Parent : ' + self.name,
                    3,
                    self.currency_id.id,
                    self.env.user.id,
                    agent_obj.id,
                    False,
                    rec['amount'],
                    0,
                    'Ledger for ' + self.name,
                )
            comm_left -= rec['amount']
        if comm_left > 0:
            ho_obj = self.reference_id.ho_id
            ledger.create_ledger_vanilla(
                self._name,
                self.id,
                'Recruit Comm. Parent : ' + self.name,
                'Recruit Comm. Parent : ' + self.name,
                3,
                self.currency_id.id,
                self.env.user.id,
                ho_obj and ho_obj.id or False,
                False,
                comm_left,
                0,
                'Ledger for ' + self.name,
            )

    def calc_ledger(self):
        ledger = self.env['tt.ledger']

        ledger.create_ledger_vanilla(
            self._name,
            self.id,
            'Recruit Fee : ' + self.name,
            'Recruit Fee : ' + self.name,
            2,
            self.currency_id.id,
            self.env.user.id,
            self.parent_agent_id.id,
            False,
            0,
            self.total_fee,
            'Ledger for ' + self.name
        )

    def create_opening_balance_ledger(self, agent_id):
        ledger = self.env['tt.ledger']

        ledger.create_ledger_vanilla(
            self._name,
            self.id,
            'Opening Balance : ' + self.name,
            'Opening Balance : ' + self.name,
            0,
            self.currency_id.id,
            self.env.user.id,
            self.parent_agent_id.id,
            False,
            0,
            self.opening_balance,
            'Ledger for ' + self.name
        )

        ledger.create_ledger_vanilla(
            self._name,
            self.id,
            'Opening Balance : ' + self.name,
            'Opening Balance : ' + self.name,
            0,
            self.currency_id.id,
            self.env.user.id,
            self.agent_id.id,
            False,
            self.opening_balance,
            0,
            'Ledger for ' + self.name
        )

    def create_partner_agent(self, user_ids):
        address_ids = []
        phone_ids = []
        social_media_ids = []
        for address in self.address_ids:
            address_ids.append(address.id)
        vals = {
            'ho_id': self.ho_id.id,
            'name': self.name,
            'est_date': datetime.now(),
            'balance': self.opening_balance,
            'agent_type_id': self.agent_type_id.id,
            'parent_agent_id': self.parent_agent_id.id,
            'reference': self.reference_id.id,
            # 'address_ids': [(6, 0, address_ids)],
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

        for idx, address in enumerate(self.address_ids):
            partner_obj.write({
                'address_ids': [(0, 0, {
                    'ho_id': address.ho_id.id if address.ho_id else self.ho_id.id,
                    'type': address.type if address.type else '',
                    'name': address.name if address.name else '',
                    'address': address.address if address.address else '',
                    'rt': address.rt if address.rt else '',
                    'rw': address.rw if address.rw else '',
                    'zip': address.zip if address.zip else '',
                    'country_id': address.country_id.id if address.country_id else '',
                    'state_id': address.state_id.id if address.state_id else '',
                    'city_id': address.city_id.id if address.city_id else '',
                    'district_id': address.district_id.id if address.district_id else '',
                    'sub_district_id': address.sub_district_id.id if address.sub_district_id else '',
                })]
            })

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
                        'ho_id': agent_id.ho_id and agent_id.ho_id.id or False,
                        'phone_number': phone['phone_number'] or '0',
                        'type': phone['type']
                    }
                    phone_obj = self.env['phone.detail'].create(vals)
                    phone_id = phone_obj.id
                    phone_list.append(phone_id)
                contact_objs.update({
                    'phone_ids': [(6, 0, phone_list)]
                })
                customer_id.append(contact_objs.id)
                con.update({
                    'customer_id': contact_objs.id,
                })
        return customer_id

    def create_agent_user(self):
        user_dict = {}
        # if self.agent_type_id.user_template:
        #     user_dict = self.agent_type_id.user_template.read()

        user_list = []
        for rec in self:
            for con in rec.agent_registration_customer_ids:
                if not con.user_level:
                    raise UserError('All user levels must be filled.')
                user_level = dict(con._fields['user_level'].selection).get(con.user_level)
                # tidak mungkin regis HO, jadi search dengan asumsi agent
                template_list = self.env['res.users'].search([('is_user_template', '=', True), ('agent_type_id', '=', rec.agent_type_id.id), ('name', 'like', 'Agent ' + user_level)], limit=1)
                user_dict = template_list and template_list[0].read() or {}
                name = (con.first_name or '') + ' ' + (con.last_name or '')

                partner_vals = {
                    'name': name,
                    'email': con.email,
                    'phone': con.phone,
                    'mobile': con.mobile,
                    'function': con.job_position
                }
                partner_id = self.env['res.partner'].create(partner_vals)

                vals = {
                    'name': name,
                    'login': con.email,
                    'email': con.email,
                    'password': ')[Lu*tsCcWt(MNM~9kJf',
                    'partner_id': partner_id.id,
                    'ho_id': rec.ho_id and rec.ho_id.id or False
                }
                if user_dict:
                    vals.update({
                        'groups_id': [(6, 0, user_dict[0]['groups_id'])],
                        'frontend_security_ids': [(6, 0, user_dict[0]['frontend_security_ids'])]
                    })
                user_id = self.env['res.users'].create(vals)
                user_list.append(user_id.id)
        user_ids = [(6, 0, user_list)]
        return user_ids

    def action_confirm(self):
        if not self.env.user.has_group('tt_base.group_agent_registration_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 34')
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
        if not self.env.user.has_group('tt_base.group_agent_registration_master_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 35')
        self.check_tac()
        self.check_registration_documents()

        self.state = 'progress'

    def action_payment(self):
        if not self.env.user.has_group('tt_base.group_agent_registration_master_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 36')
        self.state = 'payment'

    def action_validate(self):
        if not self.env.user.has_group('tt_base.group_agent_registration_master_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 37')
        percentage = 0
        if not self.payment_ids:
            raise UserError('Payment Term is Empty')
        for rec in self.payment_ids:
            if rec.state not in ['paid']:
                raise UserError('Please complete all the payments.')
            else:
                percentage += rec.percentage
        if percentage >= 100:
            if self.name:
                balance_res = self.env['tt.agent'].check_balance_limit_api(self.parent_agent_id.id, self.total_fee)
                if balance_res['error_code'] != 0:
                    _logger.error('Balance not enough')
                    raise UserError(balance_res['error_msg'])
                self.calc_commission()
                # self.partner_id = self.parent_agent_id.id
                self.create_opening_documents()
                self.state = 'validate'
            else:
                raise UserError('Please input agent name.')
        else:
            raise UserError('Please complete all the payments.')

    def action_done(self):
        if not self.env.user.has_group('tt_base.group_agent_registration_master_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 38')
        self.check_opening_documents()
        user_ids = self.create_agent_user()
        agent_id = self.create_partner_agent(user_ids)
        # self.create_customers_contact(agent_id)
        self.create_opening_balance_ledger(agent_id)
        self.state = 'done'
        # try:
        #
        # except Exception as e:
        #     self.env.cr.rollback()
        #     _logger.error(msg=str(e) + '\n' + traceback.format_exc())

    def action_cancel(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('tt_base.group_agent_registration_master_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 39')
        self.state = 'cancel'

    def action_draft(self):
        if not self.env.user.has_group('tt_base.group_agent_registration_master_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 40')
        for rec in self:
            if rec.registration_document_ids:
                for reg_doc in rec.registration_document_ids:
                    reg_doc.sudo().unlink()
            if rec.open_document_ids:
                for op_doc in rec.open_document_ids:
                    op_doc.sudo().unlink()

        self.state = 'draft'

    param_company = {
        "company_type": "company",
        "business_license": "",
        "npwp": "",
        "name": "Satelit Travel",
    }

    # "business_license": "01/2019/04/0100-02",
    # "npwp": "109358973180",

    param_pic = [
        {
            "birth_date": "21 Nov 2019",
            "first_name": "testing",
            "last_name": "it",
            "email": "qweqwd@gmail.com",
            "phone": "1249238743",
            "mobile": "8123885733",
            "job_position": "amfaksdf"
        },
        # {
        #     "birth_date": "13 Apr 1992",
        #     "first_name": "Vincent",
        #     "last_name": "Gunawan",
        #     "email": "vincentgunawan@testing.com",
        #     "phone": "",
        #     "mobile": "08153842558",
        #     "job_position": "Kepala Sales"
        # },
        # {
        #     "birth_date": "02 Feb 1995",
        #     "first_name": "Ivan",
        #     "last_name": "Setiawan",
        #     "email": "ivansetiawan@testing.com",
        #     "phone": "",
        #     "mobile": "08164826458",
        #     "job_position": "Staff"
        # },
        # {
        #     "birth_date": "28 Oct 1994",
        #     "first_name": "Andre",
        #     "last_name": "Suwadi",
        #     "email": "andresuwadi@testing.com",
        #     "phone": "",
        #     "mobile": "08168465616",
        #     "job_position": "Staff"
        # },
    ]

    param_address = {
        "city": 1,
        "zip": "60112",
        "address": "lala",
        "address2": "lili",
    }

    param_regis_doc = [
        # ["UPC.2142002", 4, "ktp"],
        ["UPC.1103001", 4, "ktp"],
        # ["UPC.2159003", 4, "siup"],
        # {
        #     'id': 2,
        #     "type": "npwp"
        # },
        # {
        #     'id': 3,
        #     "type": "siup"
        # }
    ]

    param_other = {
        "social_media": "Telegram",
        "agent_type": "Agent Citra",
        "promotion_id": "16"
    }

    param_promotion_id = 15

    param_context = {
        'co_uid': 7,
        'co_agent_id': 2
    }

    def create_agent_registration_api(self, data, context):  #
        company = data['company']  # self.param_company
        pic = data['pic']  # self.param_pic
        address = data['address']  # self.param_address
        other = data['other']  # self.param_other
        context = context  # self.param_context
        regis_doc = data['regis_doc']  # self.param_regis_doc
        promotion = data['promotion_id']  # self.param_promotion_id
        ho_obj = False
        if context.get('co_ho_id'):
            ho_obj = self.env['tt.agent'].browse(int(context['co_ho_id']))
        elif context.get('ho_seq_id'):
            ho_obj = self.env['tt.agent'].browse(int(context['ho_seq_id']))
        elif context.get('co_ho_seq_id'):
            ho_obj = self.env['tt.agent'].browse(int(context['co_ho_seq_id']))
        if ho_obj:
            address.update({
                'ho_id': ho_obj.id
            })
        check = 0
        if company.get('name'):
            registration_list = self.search([('name', '=', company['name'])], order='registration_date desc', limit=1)  # data['company']
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

        # context.update({
        #     'co_uid': self.env.user.id
        # })

        if check == 0:
            try:
                # agent_type = self.env['tt.agent.type'].sudo().search([('name', '=', other.get('agent_type'))], limit=1)
                agent_type = self.env['tt.agent.type'].sudo().browse(int(other.get('agent_type', 0)))
                parent_agent_id = self.set_parent_agent_id_api(agent_type, context['co_agent_id'])
                social_media_ids = self.create_social_media_agent_regis(other)
                # promotion_id = self.env['tt.agent.registration.promotion'].sudo().search([('id', '=', 10)], limit=1)
                promotion_id = self.get_promotion(promotion)
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
                    'promotion_id': promotion_id,
                    'reference_id': context['co_agent_id'],
                    'parent_agent_id': parent_agent_id,
                    'tac': agent_type.terms_and_condition,
                    'create_uid': context['co_uid'],
                    'ho_id': context['co_ho_id']
                })
                create_obj = self.create(header)
                regis_doc_ids = create_obj.input_regis_document_data(regis_doc)
                create_obj.write({
                    'registration_document_ids': [(6, 0, regis_doc_ids)],
                })
                create_obj.get_registration_fee_api()
                create_obj.compute_total_fee()
                if not create_obj.registration_num:
                    create_obj.registration_num = self.env['ir.sequence'].next_by_code(self._name)
                create_obj.state = 'confirm'
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
            'agent_type_id': agent_type.id,
        }
        if 'business_license' in company:
            header.update({
                'business_license': company['business_license']
            })
        if 'npwp' in company:
            header.update({
                'tax_identity_number': company['npwp']
            })
        return header

    def set_parent_agent_id_api(self, agent_type_id, agent_id):
        if agent_id:
            agent_obj = self.env['tt.agent'].browse(agent_id)
            ho_obj = agent_obj.ho_id
            """ Kalo daftar agent dengan login dulu """
            if agent_obj.is_btc_agent:
                """ Kalo B2C, parent set to HO """
                parent_agent_id = ho_obj and ho_obj.id or False
            else:
                # Set parent agent berdasarkan registration upline di agent type
                if not agent_type_id.registration_upline_ids:
                    """ Jika registration upline ids kosong, langsung set ke HO """
                    parent_agent_id = ho_obj and ho_obj.id or False
                else:
                    if self.reg_upline_contains(agent_type_id, self.env['tt.agent'].browse(agent_id).agent_type_id):
                        parent_agent_id = agent_id
                    else:
                        agent_type_obj = ho_obj and ho_obj.agent_type_id or False
                        if self.reg_upline_contains(agent_type_obj, self.env['tt.agent'].browse(agent_id).agent_type_id):
                            parent_agent_id = ho_obj and ho_obj.id or False
                        else:
                            parent_agent_id = ho_obj and ho_obj.id or False  # Sementara
        else:
            parent_agent_id = self.env.ref('tt_base.rodex_ho').id
        return parent_agent_id

    def get_config_api(self, context):
        try:
            agent_type = []
            search_params = [('can_be_registered','=',True)]
            if context.get('co_ho_id'):
                search_params.append(('ho_id', '=', int(context['co_ho_id'])))
            for rec in self.env['tt.agent.type'].search(search_params):
                agent_type.append({
                    'id': rec.id,
                    'name': rec.name,
                    'registration_fee': rec.registration_fee,
                    'is_allow_regis': rec.can_register_agent,
                    'terms_and_condition': rec.terms_and_condition,
                    'product': [{'title': rec2.title, 'benefit': rec2.benefit} for rec2 in rec.benefit]
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
                'job_position': rec.get('job_position')
            }
            customer_obj = customer_env.create(vals)
            vals_list.append(customer_obj.id)
        return vals_list

    def prepare_address(self, address):
        address_list = []
        address_id = self.address_ids.create({
            'ho_id': address.get('ho_id') and address['ho_id'] or False,
            'zip': address.get('zip'),
            'address': address.get('address'),
            # 'city_id': int(address.get('city')),
            'type': 'work'
        })
        address_list.append(address_id.id)
        return address_list

    def get_promotion(self, promotion):
        if promotion:
            return promotion
        else:
            return self.env['tt.agent.registration.promotion'].search([('agent_type_id', '=', self.agent_type_id.id), ('default', '=', True)], limit=1).id

    def input_regis_document_data(self, regis_doc):
        created_doc = self.create_registration_documents()
        document_type_env = self.env['tt.document.type'].sudo()
        doc_ids = []
        for rec_regis_doc in regis_doc:
            upload_center_ids = []
            for doc in created_doc:
                # get doc name. ex: ktp, siup, npwp, dll.
                doc_name = str(document_type_env.search([('id', '=', doc['document_id'])], limit=1).name)
                # check jika doc name sama dengan loop rec regis doc
                if doc_name == rec_regis_doc[2] or doc_name.lower() == rec_regis_doc[2]:
                    seq_id = rec_regis_doc[0]
                    doc_id = self.env['tt.upload.center'].search([('seq_id', '=', seq_id)], limit=1).id
                    upload_center_ids.append(doc_id)
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
        # self.registration_document_ids = [(6, 0, )]
        return doc_ids

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
