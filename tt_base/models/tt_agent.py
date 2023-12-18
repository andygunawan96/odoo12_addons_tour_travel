from odoo import models, fields, api, _
import logging, traceback,pytz
from ...tools import ERR,variables,util
from odoo.exceptions import UserError
from datetime import datetime,timedelta
from ...tools.ERR import RequestException
import uuid

_logger = logging.getLogger(__name__)

class TtAgent(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.agent'
    _rec_name = 'name'
    _description = 'Tour & Travel - Agent'

    name = fields.Char('Name', required=True, default='')
    legal_name = fields.Char('Legal Name')
    logo = fields.Binary('Agent Logo')  # , attachment=True

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    reference = fields.Many2one('tt.agent', 'Reference', help="Agent who Refers This Agent")
    # balance = fields.Monetary(string="Balance",  compute="_compute_balance_agent" )
    balance = fields.Monetary(string="Balance")
    annual_revenue_target = fields.Monetary(string="Annual Revenue Target", default=0)
    annual_profit_target = fields.Monetary(string="Annual Profit Target", default=0)
    # target_ids = fields.One2many('tt.agent.target', 'agent_id', string='Target(s)')
    credit_limit = fields.Monetary(string="Credit Limit",  required=False, )

    actual_credit_balance = fields.Monetary(string="Actual Credit Limit", readonly=True) ## HANYA CREDIT LIMIT
    unprocessed_amount = fields.Monetary(string="Unprocessed Amount", readonly=True)
    balance_credit_limit = fields.Monetary(string="Balance Credit Limit")

    ## UNTUK CREDIT LIMIT ##
    agent_credit_limit_provider_type_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Provider Type Access Type', default='all')
    agent_credit_limit_provider_type_eligibility_ids = fields.Many2many("tt.provider.type","tt_provider_type_tt_agent_rel","tt_agent_id", "tt_provider_type_id","Provider Type")  # what product this voucher can be applied
    agent_credit_limit_provider_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Provider Access Type', default='all')
    agent_credit_limit_provider_eligibility_ids = fields.Many2many('tt.provider', "tt_provider_tt_agent_rel","tt_agent_id", "tt_provier_id","Provider ID")  # what provider this voucher can be applied
    ## UNTUK CREDIT LIMIT ##

    npwp = fields.Char(string="NPWP", required=False, )
    est_date = fields.Datetime(string="Est. Date", required=False, )
    # mou_start = fields.Datetime(string="Mou. Start", required=False, )
    # mou_end = fields.Datetime(string="Mou. End", required=False, )
    # mou_ids = fields.One2many('tt.agent.mou', 'agent_id', string='MOU(s)')
    website = fields.Char(string="Website", required=False, )
    email = fields.Char(string="Email", required=False, )
    email_cc = fields.Char(string="Email CC(s) (Split by comma for multiple CCs)", required=False, )
    min_topup_amount = fields.Monetary('Minimum Top Up Amount', default=50000)
    topup_increment_amount = fields.Integer('Top Up Increment Amount', default=10000)
    default_unique_number = fields.Integer('Default Unique Number', default=3000)
    unique_amount_pool_min = fields.Integer('Unique Amount Pool Minimum', default=0)
    unique_amount_pool_limit = fields.Integer('Unique Amount Pool Limit', default=999)
    currency_id = fields.Many2one('res.currency', string='Default Currency', default=lambda self: self.env.user.company_id.currency_id)
    currency_ids = fields.Many2many("res.currency","res_currency_tt_agent_rel","tt_agent_id", "res_currency_id", "Other Currency")
    address_ids = fields.One2many('address.detail', 'agent_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'agent_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'agent_id', 'Social Media')
    staff_information_ids = fields.One2many('tt.customer','agent_as_staff_id','Staff Information')
    customer_parent_ids = fields.One2many('tt.customer.parent', 'parent_agent_id', 'Customer Parent')
    customer_parent_walkin_id = fields.Many2one('tt.customer.parent','Walk In Parent')
    customer_ids = fields.One2many('tt.customer', 'agent_id', 'Customer')
    default_acquirer_id = fields.Many2one('payment.acquirer','Default Acquirer')

    parent_agent_id = fields.Many2one('tt.agent', string="Parent Agent", default=lambda self: self.set_default_agent())
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    is_ho_agent = fields.Boolean('Is HO Agent')
    is_btc_agent = fields.Boolean('Is BTC Agent')
    btc_agent_type_id = fields.Many2one('tt.agent.type', 'Default BTC Agent Type')
    website_default_color = fields.Char(string='Website Default Color', default='#CDCDCD', help="HEXA COLOR")
    ho_id = fields.Many2one('tt.agent', string="Head Office", domain=[('is_ho_agent', '=', True)], required=False, default=lambda self: self.env.user.ho_id.id)
    email_server_id = fields.Many2one('ir.mail_server', string="Email Server")
    is_agent_breakdown_price_printout = fields.Boolean('Is Agent Breakdown Price Printout')
    is_btc_breakdown_price_printout = fields.Boolean('Is BTC Breakdown Price Printout')

    is_agent_required_otp = fields.Selection([('optional','Optional'), ('notification','Notification'), ('required','Required')], 'Is Agent Required OTP', default='optional', help="Optional: User can issued in system without set OTP\nNotification: User can issued in system without set OTP and always info\nRequired: User need set OTP to issued in system and always info")
    is_agent_required_pin = fields.Selection([('optional','Optional'), ('notification','Notification'), ('required','Required')], 'Is Agent Required PIN', default='optional', help="Optional: User can issued in system without set PIN\nNotification: User can issued in system without set PIN and always info\nRequired: User need set PIN to issued in system and always info")

    max_wrong_pin = fields.Integer('Max Wrong Pin Agent', default=3)
    dormant_days_inactive = fields.Integer('Auto Inactive After Dormant Days', default=90)

    redirect_url_signup = fields.Char('Redirect URL Signup', default='/')
    history_ids = fields.Char(string="History", required=False, )  # tt_history
    user_ids = fields.One2many('res.users', 'agent_id', 'User')
    payment_acquirer_ids = fields.One2many('payment.acquirer','agent_id',string="Payment Acquirer")  # payment_acquirer
    # agent_bank_detail_ids = fields.One2many('agent.bank.detail', 'agent_id', 'Agent Bank')  # agent_bank_detail
    tac = fields.Text('Terms and Conditions', readonly=True, states={'draft': [('readonly', False)],
                                                                     'confirm': [('readonly', False)]})
    active = fields.Boolean('Active', default='True')
    image_ids = fields.Many2many('tt.upload.center', 'tt_frontend_banner_tt_upload_center_rel' 'banner_id', 'image_id',
                                 string='Image',
                                 context={'active_test': False, 'form_view_ref': 'tt_base.tt_upload_center_form_view'})
    payment_acq_ids = fields.One2many('payment.acquirer.number', 'agent_id', 'Payment Acquirer Number')

    is_using_pnr_quota = fields.Boolean('Using PNR Quota', related='agent_type_id.is_using_pnr_quota', store=True)
    quota_package_id = fields.Many2one('tt.pnr.quota.price.package', 'Package', readonly=True)
    quota_ids = fields.One2many('tt.pnr.quota','agent_id','Quota', readonly=False)
    quota_total_duration = fields.Date('Max Duration', compute='_compute_quota_duration',store=True, readonly=True)
    quota_partner_ids = fields.Many2many('tt.agent', 'tt_agent_quota_partner_agent_rel', 'agent_id', 'partner_agent_id', string='Quota Partners')
    is_payment_by_system = fields.Boolean('Payment By System', default=False)
    is_send_email_cust = fields.Boolean('Send Notification Email to Customer', default=False)
    is_share_cust_ho = fields.Boolean('Share Customers with HO', default=False)

    third_party_key_ids = fields.One2many('tt.agent.third.party.key','agent_id','Third Party Key')

    point_reward = fields.Monetary(string="Point Reward")
    actual_point_reward = fields.Monetary(string="Actual Point Reward")
    unprocessed_point_reward = fields.Monetary(string="Unprocess Point Reward")

    state = fields.Selection([("draft", "Draft"), ("done", "Done")],'State', default='done')

    pricing_breakdown = fields.Boolean('Pricing Breakdown', default=False)

    def get_ho_pricing_breakdown(self):
        if not self.ho_id:
            return False
        return self.ho_id.pricing_breakdown

    # TODO VIN:tnyakan creator
    # 1. Image ckup 1 ae (logo)
    # 2. Credit limit buat agent di kasih ta? jika enggak actual balance di hapus ckup balance sja
    # 3. VA_BCA + VA_mandiri dipisah skrg dimasukan ke payment method(field baru ditambahakan waktu instal module VA)
    # 4. Annual Revenue + annual Profit Target di buat O2Many supaya kita bisa tau historical dari agent tersebut tiap taune
    # 5. Agent Code => kode citra darmo misal RDX_0001, digunakan referal code or etc?
    # 6. MOU start - Mou End = dibuat historical juga buat catat kerja sama kita pertimbangkan juga untuk masukan min/max MMF disini
    # Cth: fungsi MOU remider untuk FIPRO dkk

    # @api.multi
    # def write(self, value):
    #     self_dict = self.read()
    #     key_list = [key for key in value.keys()]
    #     for key in key_list:
    #         print(self.fields_get().get(key)['string'])
    #         self.message_post(body=_("%s has been changed from %s to %s by %s.") %
    #                                (self.fields_get().get(key)['string'],  # Model String / Label
    #                                 self_dict[0].get(key),  # Old Value
    #                                 value[key],  # New Value
    #                                 self.env.user.name))  # User that Changed the Value
    #     return super(TtAgent, self).write(value)

    @api.model
    def create(self, vals_list):
        is_ho = False
        if vals_list.get('is_ho_agent'):
            if vals_list.get('parent_agent_id'):
                raise UserError('Cannot set HO parent agent.')
            if vals_list.get('is_btc_agent'):
                vals_list.pop('is_btc_agent')
            is_ho = True

        new_agent = super(TtAgent, self).create(vals_list)
        agent_name = str(new_agent.name)
        if is_ho:
            new_agent.write({
                'ho_id': new_agent.id
            })

        walkin_obj_val = self.create_walkin_obj_val(new_agent,agent_name)

        walkin_obj = self.env['tt.customer.parent'].create(walkin_obj_val)

        new_acquirer = self.env['payment.acquirer'].create({
            'name': 'Cash',
            'provider': 'manual',
            'ho_id': is_ho and new_agent.id or new_agent.ho_id.id,
            'agent_id': new_agent.id,
            'type': 'cash',
            'website_published': True
        })

        write_vals = {
            'customer_parent_walkin_id': walkin_obj.id,
            'seq_id': self.env['ir.sequence'].next_by_code('tt.agent.type.%s' % (new_agent.agent_type_id.code)),
            'default_acquirer_id': new_acquirer.id
        }
        new_agent.write(write_vals)
        return new_agent

    def write(self, vals):
        if vals.get('is_ho_agent') and vals.get('is_btc_agent'):
            vals.pop('is_btc_agent')
        if vals.get('is_ho_agent'):
            vals.update({
                'ho_id': self.id,
                'is_btc_agent': False
            })
        if vals.get('is_btc_agent'):
            vals.update({
                'is_ho_agent': False
            })
        super(TtAgent, self).write(vals)

    @api.onchange('is_ho_agent')
    def _compute_is_btc(self):
        if self.is_ho_agent and self.is_btc_agent:
            self.is_btc_agent = False

    @api.onchange('is_btc_agent')
    def _compute_is_ho(self):
        if self.is_btc_agent and self.is_ho_agent:
            self.is_ho_agent = False

    def create_walkin_obj_val(self,new_agent,agent_name):
        return{
            'ho_id': new_agent.ho_id.id,
            'parent_agent_id': new_agent.id,
            'customer_parent_type_id': self.env.ref('tt_base.customer_type_fpo').id,
            'name': agent_name + ' FPO',
            'state': 'done'
        }

    def action_create_user(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_user_data_level_3').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 56')
        vals = {
            'name': 'Create User Wizard',
            'res_model': 'create.user.wizard',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'agent_id': self.id,
                'agent_type_id': self.agent_type_id.id
            },
        }
        return vals

    # def action_create_user(self):
    #     # view_users_form
    #     form_view_ref = self.env.ref('base.view_users_form', False)
    #     user_dict = self.agent_type_id.user_template.read()
    #     vals = {
    #         'name': 'Create User',
    #         'res_model': 'res.users',
    #         'type': 'ir.actions.act_window',
    #         'views': [(form_view_ref.id, 'form')],
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'target': '_blank',
    #         'context': {
    #             'default_agent_id': self.id,
    #         },
    #     }
    #     if user_dict:
    #         vals['context'].update({
    #             'default_groups_id': [(6, 0, user_dict[0]['groups_id'])]
    #         })
    #
    #     return vals

    @api.depends('quota_ids','quota_ids.state','quota_ids.expired_date')
    def _compute_quota_duration(self):
        for rec in self:
            if rec.quota_ids.filtered(lambda x: x.state == 'active'):
                rec.quota_total_duration = rec.quota_ids[0].expired_date

    def set_default_agent(self):
        try:
            if self.env.user.has_group('base.group_erp_manager'):
                return False
            return self.env.user.ho_id.id
        except:
            return False

    def get_is_use_point_reward(self):
        return False

    def get_balance_agent_api(self,context):
        customer_parent_id = context.get('co_customer_parent_id')
        frontend_security = context.get('co_agent_frontend_security', [])
        if 'corp_limitation' in frontend_security:  # customer parent login
            customer_parent_obj = self.env['tt.customer.parent'].browse(customer_parent_id)
            balance = 0
            point_reward = 0
            customer_parent_balance = customer_parent_obj.actual_balance
            currency_code = customer_parent_obj.currency_id.name
            customer_parent_currency_code = customer_parent_obj.currency_id.name
            credit_limit = customer_parent_obj.credit_limit
            is_show_balance = False
            is_show_customer_parent_balance = True
            is_show_credit_limit = True
            is_show_point_reward = False
        elif customer_parent_id:  # agent as customer parent login
            agent_obj = self.browse(context['co_agent_id'])
            customer_parent_obj = self.env['tt.customer.parent'].browse(customer_parent_id)
            balance = agent_obj.balance
            point_reward = 0
            customer_parent_balance = customer_parent_obj.actual_balance
            currency_code = agent_obj.currency_id.name
            customer_parent_currency_code = customer_parent_obj.currency_id.name
            credit_limit = customer_parent_obj.credit_limit
            is_show_balance = True
            is_show_customer_parent_balance = True
            is_show_credit_limit = True
            is_show_point_reward = False
        else:  # agent login
            agent_obj = self.browse(context['co_agent_id'])
            balance = agent_obj.balance
            customer_parent_balance = 0
            currency_code = agent_obj.currency_id.name
            customer_parent_currency_code = ''
            if agent_obj.credit_limit:
                credit_limit = agent_obj.actual_credit_balance
            else:
                credit_limit = 0
            is_show_balance = True
            is_show_customer_parent_balance = False
            is_show_credit_limit = True if agent_obj.credit_limit > 0 else False
            point_reward = 0
            is_show_point_reward = False
            website_use_point_reward = self.env['ir.config_parameter'].sudo().get_param('use_point_reward')
            if website_use_point_reward == 'True':
                is_show_point_reward = True
                try:
                    point_reward = agent_obj.actual_point_reward
                except:
                    point_reward = 0

        return ERR.get_no_error({
            'balance': balance,
            'customer_parent_balance': customer_parent_balance,
            'credit_limit': credit_limit,
            'customer_parent_currency_code': customer_parent_currency_code,
            'currency_code': currency_code,
            'is_show_balance': is_show_balance,
            'is_show_customer_parent_balance': is_show_customer_parent_balance,
            'is_show_credit_limit': is_show_credit_limit,
            'point_reward': point_reward,
            'is_show_point_reward': is_show_point_reward
        })

    def get_corpor_list_agent_api(self, context):
        customer_parent_data = {}
        agent_obj = self.browse(context['co_agent_id'])
        for rec in agent_obj.customer_parent_ids.filtered(lambda x: x.customer_parent_type_id.id in [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id] and (x.credit_limit != 0 or x.check_use_ext_credit_limit()) and x.state == 'done'):
            booker_data = {}
            for rec2 in rec.booker_customer_ids:
                booker_data.update({
                    rec2.customer_id.seq_id: {
                        'name': rec2.customer_id.name
                    }
                })
            customer_parent_data.update({
                rec.seq_id: {
                    'name': rec.name,
                    'booker_data': booker_data
                }
            })

        return ERR.get_no_error({
            'customer_parent_data': customer_parent_data
        })

    def get_data(self):
        res = {
            'id': self.id,
            'name': self.name,
            'agent_type_id': self.agent_type_id and self.agent_type_id.get_data() or {},
        }
        return res

    def get_agent_level(self, agent_id):
        _obj = self.sudo().browse(int(agent_id))
        response = []

        level = 0
        temp_agent_ids = []
        temp = _obj
        while True:
            values = temp.get_data()
            values.update({'agent_level': level})
            response.append(values)
            temp_agent_ids.append(temp.id)
            if not temp.parent_agent_id or temp.parent_agent_id.id in temp_agent_ids:
                break
            temp = temp.parent_agent_id
            level += 1
        return response

    def get_agent_level_api(self, agent_id):
        try:
            response = self.get_agent_level(agent_id)
            res = ERR.get_no_error(response)
        except Exception as e:
            _logger.error('%s, %s' % (str(e), traceback.format_exc()))
            res = ERR.get_error()
        return res

    def check_balance_limit(self, amount, payment_method_agent):
        # if not self.ensure_one():
        #     raise UserError('Can only check 1 agent each time got ' + str(len(self._ids)) + ' Records instead')
        # sql_query = 'select id,balance from tt_ledger where agent_id = %s order by id desc limit 1;' % (self.id)
        # self.env.cr.execute(sql_query)
        # balance = self.env.cr.dictfetchall()
        # if balance:
        #     return balance[0]['balance'] >= amount
        # else:
        #     return 0

        if not self.ensure_one():
            raise UserError('Can only check 1 agent each time got ' + str(len(self._ids)) + ' Records instead')
        if payment_method_agent == 'credit_limit':
            return self.actual_credit_balance >= amount
        else:
            return self.balance >= amount

    def check_balance_limit_api(self, agent_id, amount, payment_method_agent='balance'):
        partner_obj = self.env['tt.agent']
        if type(agent_id) == int:
            partner_obj = self.env['tt.agent'].browse(agent_id)
        elif type(agent_id) == str:
            partner_obj = self.env['tt.agent'].search([('seq_id','=',agent_id)],limit=1)

        if not partner_obj:
            return ERR.get_error(1008)
        if not partner_obj.check_balance_limit(amount, payment_method_agent):
            return ERR.get_error(1007)
        else:
            return ERR.get_no_error()

    def get_mmf_rule(self, agent_id):
        # Cari di rule
        rule = self.env['tt.monthly.fee.rule'].search([('agent_id', '=', agent_id.id),
                                                       ('state', 'in', ['confirm', 'done']),
                                                       ('start_date', '<=', fields.Date.today()),
                                                       ('end_date', '>', fields.Date.today()),
                                                       ('active', '=', True)], limit=1)
        percentage = rule and rule.perc or agent_id.agent_type_id.roy_percentage
        min_val = rule and rule.min_amount or agent_id.agent_type_id.min_value
        max_val = rule and rule.max_amount or agent_id.agent_type_id.max_value
        return percentage, min_val, max_val

    def get_current_agent_target(self):
        for rec in self:
            last_target_id = self.env['tt.agent.target'].search([('agent_id', '=', rec.id)], limit=1)
            rec.annual_revenue_target = last_target_id.annual_revenue_target
            rec.annual_profit_target = last_target_id.annual_profit_target

    # def generate_va_number(self):
    #     for phone in self.phone_ids:
    #         data = {
    #             'number': self.phone_ids[0].calling_number[-8:],
    #             'email': self.email,
    #             'name': self.name
    #         }
    #         res = self.env['tt.payment.api.con'].set_VA(data)
    #         # res = self.env['tt.payment.api.con'].delete_VA(data)
    #         # res = self.env['tt.payment.api.con'].set_invoice(data)
    #         # res = self.env['tt.payment.api.con'].merchant_info(data)
    #         if res['error_code'] == 0:
    #             for rec in self.payment_acq_ids:
    #                 #panggil espay
    #                 if rec.state == 'open':
    #                     rec.unlink()
    #             HO_acq = self.env['tt.agent'].browse(self.env.ref('tt_base.rodex_ho').id)
    #             for rec in res['response']:
    #                 check = True
    #
    #                 for payment_acq in HO_acq.payment_acquirer_ids:
    #                     if 'Virtual Account ' + self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).name == payment_acq.name:
    #                         check = False
    #                         break
    #                 # for payment_acq in self.payment_acquirer_ids:
    #                 #     if 'VA ' + self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).name == payment_acq.name:
    #                 #         check = False
    #                 if check == True:
    #                     HO_acq.env['payment.acquirer'].create({
    #                         'type': 'va',
    #                         'bank_id': self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).id,
    #                         'agent_id': self.id,
    #                         'provider': 'manual',
    #                         'website_published': True,
    #                         'name': 'Virtual Account ' + self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).name,
    #                     })
    #                     # self.env['payment.acquirer'].create({
    #                     #     'type': 'va',
    #                     #     'bank_id': self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).id,
    #                     #     'agent_id': self.id,
    #                     #     'provider': 'manual',
    #                     #     'website_published': True,
    #                     #     'name': 'VA ' + self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).name,
    #                     # })
    #                 self.env['payment.acquirer.number'].create({
    #                     'agent_id': self.id,
    #                     'payment_acquirer_id': HO_acq.env['payment.acquirer'].search([('name', '=', 'Virtual Account ' + self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).name)]).id,
    #                     'state': 'open',
    #                     'number': rec['number']
    #                 })
    #             break
    #         UserError(_("Success set VA number for this agent!"))
    #     else:
    #         UserError(_("Already set VA number for this agent!"))
    #     # if len(self.virtual_ids) == 0:
    #     #     for phone in self.phone_ids:
    #     #         if len(self.env['tt.virtual.account'].search([('virtual_account_number', 'like', self.phone_ids[0].calling_number[-8:])])) == 0:
    #     #             data = {
    #     #                 'number': self.phone_ids[0].calling_number[-8:],
    #     #                 'email': self.email,
    #     #                 'name': self.name
    #     #             }
    #     #             res = self.env['tt.payment.api.con'].set_VA(data)
    #     #             # res = self.env['tt.payment.api.con'].delete_VA(data)
    #     #             # res = self.env['tt.payment.api.con'].set_invoice(data)
    #     #             # res = self.env['tt.payment.api.con'].merchant_info(data)
    #     #             if res['error_code'] == 0:
    #     #                 for rec in res['response']:
    #     #                     if self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).id not in self.payment_acquirer_ids:
    #     #                         self.env['payment.acquirer'].create({
    #     #                             'type': 'va',
    #     #                             'bank_id': self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).id,
    #     #                             'agent_id': self.id,
    #     #                             'provider': 'manual',
    #     #                             'name': 'VA ' + self.env['tt.bank'].search([('name', '=ilike', rec['bank'])], limit=1).name,
    #     #                         })
    #     #             break
    #     # else:
    #     #     data = {
    #     #         'number': self.phone_ids[0].calling_number[-8:],
    #     #         'email': self.email,
    #     #         'name': self.name
    #     #     }
    #     #     # res = self.env['tt.payment.api.con'].merchant_info(data)
    #     #     # res = self.env['tt.payment.api.con'].delete_VA(data)
    #     #     UserError(_("Already set VA number for this agent!"))
    #
    # def delete_va_number(self):
    #     if len(self.virtual_ids) == 0:
    #         for phone in self.phone_ids:
    #             data = {
    #                 'number': self.phone_ids[0].calling_number[-8:],
    #                 'email': self.email,
    #                 'name': self.name
    #             }
    #             res = self.env['tt.payment.api.con'].delete_VA(data)
    #             if res['error_code'] == 0:
    #                 return True
    #         else:
    #             UserError(_("Please insert phone number for this agent to generate VA !"))
    #     else:
    #         UserError(_("Already set VA number for this agent!"))

    def action_show_agent_target_history(self):
        tree_view_id = self.env.ref('tt_base.view_agent_target_tree').id
        form_view_id = self.env.ref('tt_base.view_agent_target_form').id

        vals = {
            'name': _('Target History'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'tt.agent.target',
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('agent_id', '=', self.id)],
            'context': {
                'default_agent_id': self.id,
                'default_currency_id': self.currency_id.id,
            },
        }
        temp_ho_obj = self.ho_id
        if temp_ho_obj:
            vals['context'].update({
                'default_ho_id': temp_ho_obj.id
            })
        return vals

    def get_transaction_api(self,req,context):
        try:
            # _logger.info('Get Resv Req:\n'+json.dumps(req))
            agent_obj = self.browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                return ERR.get_error(1008)

            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                return ERR.get_error(1008)

            req_provider = util.get_without_empty(req,'provider_type')

            if req_provider:
                if (all(rec in variables.PROVIDER_TYPE for rec in req_provider)):
                    types = req['provider_type'] #asumsi dari frontend dapat hanya 1 update 9 juli 2021
                else:
                    raise Exception("Wrong provider type")
            else:
                types = variables.PROVIDER_TYPE


            if self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids:##klau bisa all provider
                dom = []
            elif self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids:## kalau medical only
                if set(types).intersection(['phc','periksain']):
                    dom = []
                else:
                    dom = [('agent_id', '=', agent_obj.id)]
            else:
                dom = [('agent_id', '=', agent_obj.id)]

            if req.get('pnr'):
                dom.append(('provider_booking_ids.pnr','=',req['pnr']))
            if req.get('order_number'):
                dom.append(('name','=ilike',req['order_number']))
            if req.get('booker_name'):
                dom.append(('booker_id.name','ilike',req['booker_name']))
            if req.get('passenger_name'):
                dom.append(('passenger_ids', 'ilike', req['passenger_name']))
            if req.get('date_from'):
                dom.append(('booked_date', '>=', req['date_from']))
            if req.get('date_to'):
                dom.append(('booked_date', '<=', req['date_to']))
            if req.get('provider'):
                dom.append(('provider_name', 'ilike', req['provider']))

            if not user_obj.has_group('base.group_erp_manager'):
                dom.append(('ho_id','=', agent_obj.ho_id.id))

            if req.get('state'):
                if req.get('state') != 'all':
                    if req.get('state') == 'is_need_update_identity': ## untuk filter invalid identity
                        dom.append(('passenger_ids.is_valid_identity', '=', False))
                        dom.append(('passenger_ids.identity_number', '=', 'P999999'))
                        dom.append(('state', 'not in', ['draft', 'cancel', 'cancel2']))

                    else:
                        dom.append(('state', '=', req['state']))
            if util.get_without_empty(context,'co_customer_parent_id'):
                dom.append(('customer_parent_id','=',context['co_customer_parent_id']))

            dom.append(('state', 'not in', ['halt_booked']))

            res_dict = {}
            for type in types:
                # if util.get_without_empty(req,'order_or_pnr'):
                #     list_obj = self.env['tt.reservation.%s' % (type)].search(['|',('name','=',req['order_or_pnr']),
                #                                                               ('pnr', '=', req['order_or_pnr']),
                #                                                               ('agent_id','=',context['co_agent_id'])],
                #                                                              order='create_date desc')
                # else:
                #     list_obj = self.env['tt.reservation.%s' % (type)].search([('agent_id','=',context['co_agent_id'])],
                #                                               offset=req['minimum'],
                #                                               limit=req['maximum']-req['minimum'],
                #                                             order='create_date desc')
                list_obj = self.env['tt.reservation.%s'% (type)].search(dom,order='create_date desc',
                                                                        offset=req['minimum'],
                                                                        limit=req['maximum']-req['minimum'])
                if len(list_obj.ids)>0:
                    res_dict[type] = []
                for rec in list_obj:
                    res_dict[type].append({
                        'order_number': rec.name,
                        'booked_date': rec.booked_date and rec.booked_date.strftime('%Y-%m-%d %H:%M:%S') or '',
                        'booked_uid': rec.user_id and rec.user_id.name or '',
                        'agent_name': rec.agent_id.name,
                        # 'provider': {
                        'provider_type': rec.provider_type_id and rec.provider_type_id.code or '',
                        'carrier_names': rec.carrier_name and rec.carrier_name or '',
                        # 'airline_carrier_codes':
                        # 'airline_carrier_codes': list(set([seg.carrier_code for seg in rec.segment_ids]))
                        # if hasattr(rec,'segment_ids') else [],
                        # },
                        'hold_date': rec.hold_date and rec.hold_date.strftime('%Y-%m-%d %H:%M:%S') or '',
                        'booker': rec.booker_id and rec.booker_id.to_dict() or '',
                        'pnr': rec.pnr or '',
                        'state': rec.state and rec.state or '',
                        'state_description': variables.BOOKING_STATE_STR[rec.state],
                        'issued_date': rec.issued_date and rec.issued_date.strftime('%Y-%m-%d %H:%M:%S') or '',
                        'issued_uid': rec.issued_uid and rec.issued_uid.name or '',
                        'transaction_additional_info': rec.get_transaction_additional_info(),
                        'flight_number': rec.flight_number_name if hasattr(rec,'flight_number_name') else '',
                        'departure_date': rec.departure_date if hasattr(rec,'departure_date') else '',
                        'total_pax': rec.total_pax,
                        'passenger_list': ["%s %s %s" % (passenger.title, passenger.first_name, passenger.last_name) for passenger in rec.passenger_ids]
                    })

            # _logger.info('Get Transaction Resp:\n'+json.dumps(res_list[req.get('minimum',0):req.get('maximum',20)]))
            # return ERR.get_no_error(res_list[req.get('minimum',0):req.get('maximum',20)])

            # _logger.info('Get Transaction Resp:\n' + json.dumps(res_dict))
            return ERR.get_no_error(res_dict)
        except Exception as e:
            _logger.error(str(e)+traceback.format_exc())
            return ERR.get_error(1012)

    @api.model
    def agent_action_view_customer(self):
        return {
            'name': 'Agent',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'kanban,form',
            'res_model': 'tt.agent',
            'views': [(self.env.ref('tt_base.tt_agent_kanban_view_customer').id, 'kanban'),
                      (self.env.ref('tt_base.tt_agent_form_view_customer').id, 'form')],
            'context': {},
            'domain': ['|', ('parent_agent_id', '=', self.env.user.agent_id.id), ('id', '=', self.env.user.agent_id.id)]
        }

    def use_pnr_quota(self, req):
        if self.is_using_pnr_quota:
            quota_obj_list = self.quota_ids.filtered(lambda x: x.state == 'active')

            if len(quota_obj_list) == 0:## kalau tidak ada quota_obj yg aktif di buatkan 1
                new_quota_id = self.env['tt.pnr.quota'].create_pnr_quota_api(
                    {
                        'quota_seq_id': self.quota_package_id.seq_id,
                        'is_called_from_backend': True
                    },
                    {
                        'co_agent_id': self.id
                    }
                )
                quota_obj = self.env['tt.pnr.quota'].browse(int(new_quota_id))
            else:
                #ambl yg index 0, terbaru
                quota_obj = quota_obj_list[0]
            total_quota_pnr_used = quota_obj.usage_quota
            type_price = 'pax'
            ## update calculate_price ke semua hanya catat transaction fee
            calculate_price_dict = self.env['tt.pnr.quota'].calculate_price(quota_obj.price_package_id.available_price_list_ids, req)
            amount = calculate_price_dict['price']
            usage_pnr_quota = calculate_price_dict['quota_pnr_usage'] ## check semua
            type_price = calculate_price_dict['type_price']
            if self.quota_package_id.is_calculate_all_inventory or req['inventory'] == 'external':
                if self.quota_package_id.free_usage >= total_quota_pnr_used + usage_pnr_quota:
                    amount = 0
                elif self.quota_package_id.free_usage > total_quota_pnr_used and type_price != 'pnr':
                    amount = ((total_quota_pnr_used + usage_pnr_quota - self.quota_package_id.free_usage) / usage_pnr_quota) * amount
            else:
                ## not calculate internal inventory
                amount = 0
                usage_pnr_quota = 0
            self.env['tt.pnr.quota.usage'].create({
                'ho_id': quota_obj.ho_id and quota_obj.ho_id.id or quota_obj.agent_id.ho_id.id,
                'res_model_resv': req.get('res_model_resv'),
                'res_id_resv': req.get('res_id_resv'),
                'res_model_prov': req.get('res_model_prov'),
                'res_id_prov': req.get('res_id_prov'),
                'pnr_quota_id': quota_obj.id,
                'ref_pnrs': req.get('ref_pnrs'),
                'ref_carriers': req.get('ref_carriers'),
                'ref_name': req.get('ref_name'),
                'ref_provider': req['ref_provider'],
                'ref_provider_type': req['ref_provider_type'],
                'ref_pax': req.get('ref_pax') and int(req.get('ref_pax')) or 0,
                'ref_r_n': req.get('ref_r_n') and int(req.get('ref_r_n')) or 0,
                'amount': amount,
                'inventory': req['inventory'],
                'usage_quota': usage_pnr_quota
            })

    def get_available_pnr_price_list_api(self,context):
        try:
            agent_obj = self.browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                raise RequestException(1008)

            if not agent_obj.is_using_pnr_quota or not agent_obj.quota_package_id:
                raise RequestException(1012,additional_message="Agent not allowed.")

            package_res = agent_obj.quota_package_id.to_dict()

            return ERR.get_no_error(package_res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1012,additional_message="PNR Price List")


    # def generate_rodexshop_key(self): #Rodexshop deprecated
    #     if not self.env.user.agent_id.id == self.id:
    #         raise UserError("Can only generate for own agent.")
    #     if not self.third_party_key_ids.filtered(lambda x: x.name == 'RodexShop External Key'):
    #         key_exist =True
    #         key = ''
    #         while(key_exist):
    #             key = uuid.uuid4().hex
    #             exist_key_list = self.env['tt.agent.third.party.key'].sudo().search([('key','=',key)])
    #             if not exist_key_list:
    #                 key_exist = False
    #
    #         self.env['tt.agent.third.party.key'].sudo().create({
    #             'name': 'RodexShop External Key',
    #             'key': key,
    #             'agent_id': self.id,
    #         })

    def get_reconcile_data_api(self, data, context):
        try:
            provider_type = data['provider_type']
            start_date = util.convert_timezone(data['start_date'],origin_tz='Asia/Jakarta',dest_tz='UTC')
            end_date = data.get('end_date') and util.convert_timezone(data['end_date'],origin_tz='Asia/Jakarta',dest_tz='UTC') or start_date
            if start_date == end_date:## kalau request tanggal sama akan return list kosong karena <= A >= A timestamp yg sama
                end_date = end_date + timedelta(days=1)
            resv_table = 'tt.reservation.{}'.format(provider_type, )

            resv_data = self.env[resv_table].search([('agent_id', '=', context['co_agent_id']), ('state', '=', 'issued'), ('issued_date', '>=', start_date), ('issued_date', '<=', end_date), ('reconcile_state', '=', 'reconciled')])
            res = []
            for rec in resv_data:
                latest_ledger = self.env['tt.ledger'].search([('res_id', '=', rec.id), ('res_model', '=', resv_table), ('transaction_type', '=', 2), ('is_reversed', '=', False)], limit=1)
                end_balance = latest_ledger and latest_ledger[0].balance or 0
                issued_time = pytz.timezone('Asia/Jakarta').normalize(pytz.utc.localize(rec.issued_date))

                rec_data = {
                    'order_number': rec.name,
                    'pnr': rec.pnr,
                    'type': 'nta',
                    'issued_time': issued_time,
                    'nta_price': rec.agent_nta,
                    'end_balance': end_balance,
                    'carrier_list': rec.carrier_name,
                    'currency': rec.currency_id.name
                }

                str_issued_date = issued_time.strftime('%Y-%m-%d')
                not_found = True
                for rec_res in res:
                    if rec_res['transaction_date'] == str_issued_date:
                        rec_res['transactions'].append(rec_data)
                        not_found = False
                if not_found:
                    res.append({
                        'transaction_date': str_issued_date,
                        'transactions': [rec_data]
                    })

            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def generate_va_all(self):
        error_msg = []
        success_msg = []
        for agent_obj in self.search([]):
            _logger.info("GENERATE VA %s" % (agent_obj.name))
            try:
                next_agent = False
                for payment_acq_number in agent_obj.payment_acq_ids:
                    if payment_acq_number.state == 'open':
                        success_msg.append('%s Success, already Exist.\n\n' % (agent_obj.name))
                        next_agent = True
                        break
                if next_agent:
                    continue
                if agent_obj.phone_ids:
                    agent_obj.phone_ids[0].generate_va_number()
                    success_msg.append('%s Success, VA Created.\n\n' % (agent_obj.name))
                else:
                    error_msg.append('%s Failed, No Phone.\n\n' % (agent_obj.name))
            except Exception as e:
                error_msg.append(agent_obj.name+ " " + str(e) + "\n\n")
        file = open('/var/log/odoo/%s_va_success.txt' % (datetime.now().strftime('%Y_%m_%d__%H_%M_%S')),'w')
        for row in success_msg:
            file.write(row)
        file.close()

        file = open('/var/log/odoo/%s_va_error.txt' % (datetime.now().strftime('%Y_%m_%d__%H_%M_%S')), 'w')
        for row in error_msg:
            file.write(row)
        file.close()

    def check_send_email_cc(self):
        email_cc = False
        email_cc_list = []
        if self.email_cc:
            email_cc_list += self.email_cc.split(",")
        if email_cc_list:
            email_cc_list = list(set(email_cc_list)) ## remove duplicate
            email_cc = ",".join(email_cc_list)
        return email_cc

    def get_printout_agent_color(self, context={}):
        base_color = '#CDCDCD'
        if not context:
            agent_ho_obj = self.ho_id.sudo()
        elif context.get('co_ho_id'):
            agent_ho_obj = self.browse(context['co_ho_id'])
        if agent_ho_obj.website_default_color:
            base_color = agent_ho_obj.website_default_color if agent_ho_obj.website_default_color[0] == '#' else '#%s' % agent_ho_obj.website_default_color
        return base_color

    def get_simple_agent_list_data(self):
        '''
        start_index=None, limit=None
        '''
        payload = {
            'agent_list': [],
            'error_code': 0,
            'error_msg': '',
        }
        try:
            # if start_index != None and type(start_index) != int:
            #     raise Exception('Wrong type value start_index, must be int')
            # if limit != None and type(limit) != int:
            #     raise Exception('Wrong type value limit, must be int')

            objs = self.env['tt.agent'].sudo().search([])
            # if start_index != None:
            #     objs = objs[start_index:]
            # if limit != None:
            #     objs = objs[:limit]

            for obj in objs:
                vals = {
                    'name': obj.name,
                    'agent_id': obj.id,
                    'agent_type_id': 0,
                    'agent_type_name': "",
                    'agent_type_code': "",
                }
                if obj.agent_type_id:
                    vals.update({
                        'agent_type_id': obj.agent_type_id.id,
                        'agent_type_name': obj.agent_type_id.name,
                        'agent_type_code': obj.agent_type_id.code,
                    })
                payload['agent_list'].append(vals)
        except Exception as e:
            payload.update({
                'error_code': 500,
                'error_msg': str(e)
            })
        return payload

    def get_agent_api(self):
        res = []
        # agent_objs = self.search([]) ## ALL AGENT
        agent_objs = self.search([('is_ho_agent','=', True)]) ## HANYA HO
        for agent_obj in agent_objs:
            other_currency = []
            for currency_obj in agent_obj.currency_ids:
                other_currency.append(currency_obj.name)
            res.append({
                "name": agent_obj.name,
                "seq_id": agent_obj.seq_id,
                "is_ho_agent": agent_obj.is_ho_agent,
                "id": agent_obj.id,
                "currency_id": agent_obj.currency_id.name,
                "other_currency": other_currency
            })
        res = ERR.get_no_error({"agent_dict": res})
        return res

    def get_ho_currency_api(self):
        res = {}
        agent_objs = self.search([('is_ho_agent', '=', True)])  ## HANYA HO
        for agent_obj in agent_objs:
            currency_list = []
            if agent_obj.currency_id:
                currency_list.append(agent_obj.currency_id.name)
            for currency_obj in agent_obj.currency_ids:
                if currency_obj.name not in currency_list:
                    currency_list.append(currency_obj.name)
            res[agent_obj.seq_id] = {
                "currency_list": currency_list,
                "default_currency": agent_obj.currency_id.name
            }
        res = ERR.get_no_error({"currency_dict": res})
        return res

class AgentTarget(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.agent.target'
    _order = 'start_date desc'
    _description = 'Historical Target Agent per Satuan waktu (tahun/bulan)'

    name = fields.Char('Target Name')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')

    annual_revenue_target = fields.Monetary("Annual Revenue Target")
    annual_profit_target = fields.Monetary("Annual Profit Target")

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id.id)

class AgentMOU(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.agent.mou'
    _description = 'Agent Memorandum of Understanding'
    # Catet Perjanian kerja sama antara citra dengan agent contoh: Fipro target e brpa klo kurang dia mesti bayar

    name = fields.Char('Target Name')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', domain=[('parent_id', '=', False)], required=True)

    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    min_amount = fields.Monetary('Min MMF', copy=False)
    max_amount = fields.Monetary('Max MMF', copy=False)
    perc = fields.Float('Percentage', copy=False)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('inactive', 'In Active')],
                             string='State', default='draft')
    confirm_uid = fields.Many2one('res.users', 'Confirmed by')
    confirm_date = fields.Datetime('Confirm Date')
    active = fields.Boolean('Active', default=True)

    def get_mmf_rule(self, agent_id, date=False):
        if not date:
            date = fields.Date.today()
        # Cari di rule
        rule = self.search([('agent_id', '=', agent_id.id), ('state', '=', 'confirm'),
                            ('start_date', '<=', date), ('end_date', '>', date),
                            ('active', '=', True)], limit=1)
        # Todo: pertimbangkan tnya base rule untuk masing2x citra dimna?
        # percentage = rule and rule.perc or agent_id.agent_type_id.roy_percentage
        percentage = rule and rule.perc or 0
        min_val = rule and rule.min_amount or 0
        max_val = rule and rule.max_amount or 0
        return percentage, min_val, max_val
