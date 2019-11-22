from odoo import models, fields, api, _
import logging, traceback
from ...tools import ERR,variables,util
from odoo.exceptions import UserError
import json

_logger = logging.getLogger(__name__)


class TtAgent(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.agent'
    _rec_name = 'name'
    _description = 'Tour & Travel - Agent'

    name = fields.Char('Name', required=True, default='')
    logo = fields.Binary('Agent Logo')  # , attachment=True

    seq_id = fields.Char('Sequence ID')
    reference = fields.Many2one('tt.agent', 'Reference', help="Agent who Refers This Agent")
    # balance = fields.Monetary(string="Balance",  compute="_compute_balance_agent" )
    balance = fields.Monetary(string="Balance", related="" )
    annual_revenue_target = fields.Monetary(string="Annual Revenue Target", default=0)
    annual_profit_target = fields.Monetary(string="Annual Profit Target", default=0)
    # target_ids = fields.One2many('tt.agent.target', 'agent_id', string='Target(s)')
    credit_limit = fields.Monetary(string="Credit Limit",  required=False, )
    npwp = fields.Char(string="NPWP", required=False, )
    est_date = fields.Datetime(string="Est. Date", required=False, )
    # mou_start = fields.Datetime(string="Mou. Start", required=False, )
    # mou_end = fields.Datetime(string="Mou. End", required=False, )
    # mou_ids = fields.One2many('tt.agent.mou', 'agent_id', string='MOU(s)')
    website = fields.Char(string="Website", required=False, )
    email = fields.Char(string="Email", required=False, )
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    address_ids = fields.One2many('address.detail', 'agent_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'agent_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'agent_id', 'Social Media')
    customer_parent_ids = fields.One2many('tt.customer.parent', 'parent_agent_id', 'Customer Parent')
    customer_parent_walkin_id = fields.Many2one('tt.customer.parent','Walk In Parent')
    customer_ids = fields.One2many('tt.customer', 'agent_id', 'Customer')
    default_acquirer_id = fields.Many2one('payment.acquirer','Default Acquirer')

    parent_agent_id = fields.Many2one('tt.agent', string="Parent Agent", default=lambda self: self.set_default_agent())
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', required=True)
    history_ids = fields.Char(string="History", required=False, )  # tt_history
    user_ids = fields.One2many('res.users', 'agent_id', 'User')
    payment_acquirer_ids = fields.One2many('payment.acquirer','agent_id',string="Payment Acquirer")  # payment_acquirer
    agent_bank_detail_ids = fields.One2many('agent.bank.detail', 'agent_id', 'Agent Bank')  # agent_bank_detail
    tac = fields.Text('Terms and Conditions', readonly=True, states={'draft': [('readonly', False)],
                                                                     'confirm': [('readonly', False)]})
    active = fields.Boolean('Active', default='True')

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
        new_agent = super(TtAgent, self).create(vals_list)
        agent_name = str(new_agent.name)

        walkin_obj_val = self.create_walkin_obj_val(new_agent,agent_name)

        walkin_obj = self.env['tt.customer.parent'].create(walkin_obj_val)

        new_acquirer = self.env['payment.acquirer'].create({
            'name': '%s Cash' % (new_agent.name),
            'provider': 'manual',
            'agent_id': new_agent.id,
            'type': 'cash',
            'website_published': True
        })

        new_agent.write({
            'customer_parent_walkin_id': walkin_obj.id,
            'seq_id': self.env['ir.sequence'].next_by_code('tt.agent.type.%s' % (new_agent.agent_type_id.code)),
            'default_acquirer_id': new_acquirer.id
        })
        return new_agent

    def create_walkin_obj_val(self,new_agent,agent_name):
        return{
            'parent_agent_id': new_agent.id,
            'customer_parent_type_id': self.env.ref('tt_base.customer_type_fpo').id,
            'name': agent_name + ' FPO',
        }

    def action_create_user(self):
        print(self.agent_type_id.code)
        vals = {
            'name': 'Create User Wizard',
            'res_model': 'create.user.wizard',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'agent_id': self.id,
                'agent_type_id': self.agent_type_id.id,
                'agent_type_code': self.agent_type_id.code,
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

    def _compute_balance_agent(self):
        for rec in self:
            if len(rec.ledger_ids)>0:
                rec.balance = rec.ledger_ids[0].balance
            else:
                rec.balance = 0

    def set_default_agent(self):
        try:
            return self.env.ref('tt_base.rodex_ho').id
        except:
            return False

    def get_balance_agent_api(self,context):
        agent_obj = self.browse(context['co_agent_id'])
        return ERR.get_no_error({
            'balance': agent_obj.balance,
            'credit_limit': 0,
            'currency_code': agent_obj.currency_id.name
        })

    def get_data(self):
        res = {
            'id': self.id,
            'name': self.name,
            'agent_type_id': self.agent_type_id and self.agent_type_id.get_data() or {},
        }
        return res

    def get_agent_level_api(self, agent_id):
        try:
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
            res = ERR.get_no_error(response)
        except Exception as e:
            _logger.error('%s, %s' % (str(e), traceback.format_exc()))
            res = ERR.get_error()
        return res

    def check_balance_limit(self, amount):
        if not self.ensure_one():
            raise UserError('Can only check 1 agent each time got ' + str(len(self._ids)) + ' Records instead')
        return self.balance >= amount

    def check_balance_limit_api(self, agent_id, amount):
        partner_obj = self.env['tt.agent'].browse(agent_id)
        if not partner_obj:
            return ERR.get_error(1008)
        if not partner_obj.check_balance_limit(amount):
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

    def action_show_agent_target_history(self):
        tree_view_id = self.env.ref('tt_base.view_agent_target_tree').id
        form_view_id = self.env.ref('tt_base.view_agent_target_form').id
        return {
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

    def get_transaction_api(self,req,context):
        try:
            _logger.info('Get Resv Req:\n'+json.dumps(req))
            agent_obj = self.browse(context['co_agent_id'])
            if not agent_obj:
                return ERR.get_error(1008)

            req_provider = util.get_without_empty(req,'provider_type')

            if req_provider and req_provider in variables.PROVIDER_TYPE:
                types = req['provider_type']
            else:
                types = variables.PROVIDER_TYPE

            res_list = []
            for type in types:
                if util.get_without_empty(req,'order_or_pnr'):
                    list_obj = self.env['tt.reservation.%s' % (type)].search(['|',('name','=',req['order_or_pnr']),
                                                                              ('pnr', '=', req['order_or_pnr']),
                                                                              ('agent_id','=',context['co_agent_id'])])
                else:
                    list_obj = self.env['tt.reservation.%s' % (type)].search([('agent_id','=',context['co_agent_id'])],
                                                              offset=req['minimum'],
                                                              limit=req['maximum']-req['minimum'])
                for rec in list_obj:
                    res_list.append({
                        'order_number': rec.name,
                        'booked_date': rec.booked_date and rec.booked_date.strftime('%d-%m-%Y %H:%M:%S') or '',
                        'booked_uid': rec.booked_uid and rec.booked_uid.name or '',
                        'provider': {
                            'provider_type': rec.provider_type_id and rec.provider_type_id.code or '',
                            'airline_carrier_codes': list(set([seg.carrier_code for seg in rec.segment_ids]))
                            if hasattr(rec,'segment_ids') else [],
                        },
                        'hold_date': rec.hold_date and rec.hold_date.strftime('%d-%m-%Y %H:%M:%S') or '',
                        'booker': rec.booker_id and rec.booker_id.to_dict() or '',
                        'pnr': rec.pnr or '',
                        'state_description': variables.BOOKING_STATE_STR[rec.state],
                        'issued_date': rec.issued_date and rec.issued_date.strftime('%d-%m-%Y %H:%M:%S') or '',
                        'issued_uid': rec.issued_uid and rec.issued_uid.name or ''
                    })

            sorted(res_list, key=lambda i: i['hold_date'])

            _logger.info('Get Transaction Resp:\n'+json.dumps(res_list))
            return ERR.get_no_error(res_list)
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
            'views': [(self.env.ref('tt_base.tt_agent_kanban_view').id, 'kanban'),
                      (self.env.ref('tt_base.tt_agent_form_view').id, 'form')],
            'context': {},
            'domain': ['|', ('parent_agent_id', '=', self.env.user.agent_id.id), ('id', '=', self.env.user.agent_id.id)]
        }


class AgentTarget(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.agent.target'
    _order = 'start_date desc'
    _description = 'Historical Target Agent per Satuan waktu (tahun/bulan)'

    name = fields.Char('Target Name')
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