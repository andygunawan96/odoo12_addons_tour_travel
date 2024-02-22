from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
import copy


class MonthlyManagementFeeRule(models.Model):
    _name = 'tt.monthly.fee.rule'
    _description = 'Monthly Fee Rule'

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent')
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type')
    confirm_uid = fields.Many2one('res.users', 'Confirmed by')
    confirm_date = fields.Datetime('Confirm Date')

    inactive_uid = fields.Many2one('res.users', 'In-Active by')
    inactive_date = fields.Datetime('In-Active Date')

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Active'),
                              ('inactive', 'In Active')],
                             string='State', default='draft')
    min_amount = fields.Monetary('Min MMF', copy=False)
    max_amount = fields.Monetary('Max MMF', copy=False)
    perc = fields.Float('Percentage', copy=False)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    start_date = fields.Date('Start')
    end_date = fields.Date('End')

    active = fields.Boolean('Active', default=True)

    @api.one
    def set_to_draft(self):
        self.state = 'draft'

    @api.one
    def set_to_inactive(self):
        self.state = 'inactive'

    @api.one
    def action_confirm(self):
        self.update({
            'state': 'confirm',
            'confirm_date': fields.Datetime.now(),
            'confirm_uid': self.env.user.id,
        })

    @api.multi
    def get_rule_for_agent(self, agent_id, date):
        default_params = [('state', '=', 'confirm'), ('start_date', '<=', date),
                          '|', ('end_date', '>=', date), ('end_date', '=', False)]
        # Find By Agent_id
        temp_params = copy.deepcopy(default_params)
        temp_params.append(('agent_id', '=', agent_id.id))
        rule_id = self.search(temp_params, limit=1)
        if not rule_id:
            # Jika g ketemu Find By Agent_type_id
            temp_params = copy.deepcopy(default_params)
            temp_params.append(('agent_type_id', '=', agent_id.agent_type_id.id))
            rule_id = self.search(temp_params, limit=1)
        return rule_id and rule_id[0] or False


class MonthlyManagementFee(models.Model):
    _name = 'tt.monthly.fee'
    _order = 'id desc'
    _description = 'Monthly Fee Model'

    name = fields.Char('Name', required=True)

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, readonly=True, states={'draft':[('readonly',False)]})
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', copy=False)
    confirm_date = fields.Datetime('Confirm Date', copy=False)

    validate_uid = fields.Many2one('res.users', 'Validate by', copy=False)
    validate_date = fields.Datetime('Validate Date', copy=False)

    recheck_uid = fields.Many2one('res.users', 'Re-Check by', copy=False)
    recheck_date = fields.Datetime('Re-Check Date', copy=False)

    done_uid = fields.Many2one('res.users', 'Done by', help='Forced Done By', copy=False)
    done_date = fields.Datetime('Done Date', copy=False)

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('send', 'Send'),
                              ('valid', 'Validate'), ('recheck', 'Re-Check'), ('done', 'Done')], string='State',
                             default='draft',
                             help='Draft : Draft, ' \
                                  'Confirm : HO Validate the Calculation; Waiting system Send, ' \
                                  'Send : Sended by System; wait agent validation, ' \
                                  'Re-Check : Need more re-check; User input recheck Value, ' \
                                  'Validate : User Validate; Waiting System Process ')

    rule_id = fields.Many2one('tt.monthly.fee.rule', 'Rule',help='Rule apply based on start date only')
    min_amount = fields.Monetary('Min MMF', copy=False, readonly=True, states={'draft':[('readonly',False)]})
    max_amount = fields.Monetary('Max MMF', copy=False, readonly=True, states={'draft':[('readonly',False)]})
    perc = fields.Float('Percentage', copy=False, readonly=True, states={'draft':[('readonly',False)]})
    amount = fields.Monetary('Amount', copy=False, compute='calc_amount', readonly=True, states={'draft':[('readonly',False)]})
    transaction_amount = fields.Monetary('Transaction Amount', copy=False, compute='calc_amount', readonly=True, states={'draft':[('readonly',False)]})
    total_amount = fields.Monetary('Total Amount', copy=False, compute='calc_amount')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    mmf_line_ids = fields.One2many('tt.monthly.fee.line', 'mmf_id', copy=False)
    line_count = fields.Integer('Line(s)', compute='count_line')

    period = fields.Char('Period', help='format: YYYY-MM; examp: 2020-01(January 2020)', readonly=True, states={'draft':[('readonly',False)]})
    start_date = fields.Date('Start', readonly=True, states={'draft':[('readonly',False)]})
    end_date = fields.Date('End', readonly=True, states={'draft':[('readonly',False)]})

    msg = fields.Text('Re-Check Messesage')

    ledger_id = fields.Many2one('tt.ledger', 'Ledger', copy=False, readonly=True, ondelete='cascade')
    ho_ledger_id = fields.Many2one('tt.ledger', 'HO Ledger', copy=False, readonly=True, ondelete='cascade')

    # incentive_id = fields.Many2one('tt.incentive', 'Incentive')
    # incentive_amount = fields.Float('Incentive Amount', related='incentive_id.total_amount')

    is_enough = fields.Boolean('Is Enough', default=True)
    email_to_id = fields.Many2one('res.partner', string='Temp. fields')

    @api.onchange('mmf_line_ids', 'perc', 'min_amount', 'max_amount')
    def calc_amount(self):
        for rec in self:
            trans = 0
            for line in rec.mmf_line_ids:
                trans += line.amount
            rec.transaction_amount = trans
            # trans += rec.incentive_amount
            rec.amount = (trans * rec.perc) / 100
            rec.total_amount = rec.amount < rec.min_amount and rec.min_amount or \
                               rec.amount > rec.max_amount and rec.max_amount or rec.amount

    # def calc_incentive(self):
    #     for rec in self:
    #         incentive_obj = self.env['tt.incentive'].search([('agent_id', '=', rec.agent_id.id), ('start_date', '=', rec.start_date), ('end_date', '=', rec.end_date)], limit=1)
    #         if incentive_obj:
    #             rec.incentive_id = incentive_obj.id

    @api.multi
    def count_line(self):
        for rec in self:
            rec.line_count = len(rec.mmf_line_ids)

    # def send_push_notif(self, type):
    #     base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #     obj_id = str(self.id)
    #     model = 'tt.incentive'
    #     url = base_url + '/web#id=' + obj_id + '&view_type=form&model=' + model
    #     desc = type + ' MMF ' + self.name + ' Rp {:,.0f}'.format(self.total_amount)
    #     # Vanesa 20/04
    #     data = {
    #         'main_title': 'Monthly Management Fee',
    #         'message': desc,
    #         'notes': url
    #     }
    #     TelegramInfoNotification(data).send_message()
        # End

    @api.multi
    def return_action_to_open(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Monthly Management Fee(s)',
            'res_model': 'tt.monthly.fee.line',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': False,
            'context': {},
            'domain': [('mmf_id', '=', self.id)],
            'target': 'current',
        }

    @api.depends('period', 'agent_id')
    @api.onchange('period', 'agent_id')
    def compute_display_name(self):
        name = self.agent_id and self.agent_id.name or ''
        period = self.period and self.period or ''
        self.name = name + '(' + period + ')'

    def compute_line(self):
        self.calc_mmf(fields.Date.today(), self.agent_id)

    @api.multi
    def create_ledger(self, agent, royalty, currency_id):
        vals = self.env['tt.ledger'].prepare_vals('MMF : ' + str(self.name), 'MMF : ' + str(self.name),
                                                  'monthly.fee',
                                                  currency_id.id, 0, royalty)
        vals['agent_id'] = agent.id
        new_aml = self.env['tt.ledger'].create(vals)
        # new_aml.action_done()
        self.ledger_id = new_aml

        vals = self.env['tt.ledger'].prepare_vals('MMF : ' + str(self.name), 'MMF ' + str(self.period),
                                                  'commission',
                                                  currency_id.id, royalty, 0)
        vals['agent_id'] = self.env['res.partner'].sudo().search([('is_HO', '=', True), ('parent_id', '=', False)], limit=1).id
        new_aml = self.env['tt.ledger'].create(vals)
        # new_aml.action_done()
        self.ho_ledger_id = new_aml

    @api.one
    def set_to_draft(self):
        self.state = 'draft'

    @api.one
    def action_confirm(self):
        self.update({
            'state': 'confirm',
            'confirm_date': fields.Datetime.now(),
            'confirm_uid': self.env.user.id,
        })

    @api.one
    def action_send_email(self, with_notif=True):
        template = self.env.ref('tt_orbis_aftersales.email_aftersales_1', False)
        mail_id = self.env['ir.mail_server'].search([('name', 'ilike', 'info')], limit=1)
        if mail_id:
            template.mail_server_id = mail_id[0].id
        else:
            mail_id = self.env['ir.mail_server'].search([], limit=1)
            template.mail_server_id = mail_id[0].id
        a = self.env['mail.template'].browse(template.id)
        for rec in self.agent_id.child_ids.filtered(lambda x: x.type in ['pic', 'owner']):
            self.email_to_id = rec.id
            a.send_mail(self.id, force_send=True)
        self.state = 'send'
        if with_notif:
            self.send_push_notif('Send')
        self.email_to = ''

    @api.one
    def action_validate(self):
        self.update({
            'state': 'valid',
            'validate_date': fields.Datetime.now(),
            'validate_uid': self.env.user.id,
        })

    @api.one
    def action_done(self):
        self.create_ledger(self.agent_id, self.total_amount, self.currency_id)
        self.update({
            'state': 'done',
            'done_date': fields.Datetime.now()
        })
        if self.agent_id.balance < 0:
            self.is_enough = False

    @api.one
    def action_force_done(self):
        self.action_done()
        self.done_uid = self.env.user.id

    @api.multi
    def create_mmf(self, date, agent):
        vals = {
            'name': agent.name + '(' + date[:7] + ')',
            'agent_id': agent.id,
            'state': 'draft',
            'period': date[:7],
            'start_date': date,
            'end_date': fields.Datetime.now(),
        }
        mmf_id = self.env['tt.monthly.fee'].create(vals)
        return mmf_id

    @api.multi
    def create_mmf_line(self, mmf_id, ledger_id):
        obj_id = self.env[ledger_id.res_model].sudo().browse(ledger_id.res_id)
        vals = {
            'mmf_id': mmf_id.id,
            'resv_name': obj_id.name,
            'ledger_id': ledger_id.id,
            'agent_name': ledger_id.sudo().agent_id.name,
            'date': str(ledger_id.date)[:10],
            'transaction_type': dict(ledger_id._fields['transaction_type'].selection).get(ledger_id.transaction_type),
            'carrier_name': obj_id.provider_name,
            'pnr': obj_id.pnr,
        }
        mmf_id = self.env['tt.monthly.fee.line'].create(vals)
        mmf_id.get_contact_id()
        return mmf_id

    @api.multi
    def get_mmf_rule(self):
        for rec in self:
            # Cari di rule
            rule = self.env['tt.monthly.fee.rule'].get_rule_for_agent(rec.agent_id, rec.start_date)
            if rule:
                rec.rule_id = rule.id
                rec.perc = rule.perc
                rec.min_amount = rule.min_amount
                rec.max_amount = rule.max_amount
            else:
                # TODO Notif cannot find rule for this agent cman di list
                continue

    @api.multi
    def calc_mmf_line(self):
        total_transac = 0
        for ledger in self.env['tt.ledger'].search([('agent_id', '=', self.agent_id.id),
                                                    ('transaction_type', '=', 3),
                                                    ('date', '>=', self.start_date), ('date', '<=', self.end_date)]):
            total_transac += ledger.debit
            total_transac -= ledger.credit
            self.create_mmf_line(self, ledger)
        for adj in self.env['tt.adjustment'].search([('agent_id', '=', self.agent_id.id),
                                                          ('component_type', '=', 'commission'),
                                                          ('state', 'in', ['approve',]),
                                                          ('approve_date', '>=', self.start_date),
                                                          ('approve_date', '<', self.end_date)]):
            for ledger in adj.ledger_ids:
                if ledger.agent_id.id == self.agent_id.id:
                    total_transac += ledger.debit
                    total_transac -= ledger.credit
                    self.create_mmf_line(self, ledger)

    def remove_line_2(self):
        for line in self.mmf_line_ids:
            line.sudo().unlink()

    def remove_line(self):
        if self.state == 'draft':
            self.remove_line_2()
        else:
            raise UserError(_('Cannot delete a Line not in draft or cancel state'))

    @api.multi
    def calc_mmf(self, date, agent):
        mmf_id = self.create_mmf(date, agent)
        mmf_id.calc_mmf_line()

    @api.multi
    def send_mmf(self):
        for rec in self.search([('state', 'in', ['confirm',])]):
            rec.action_force_send()

    @api.multi
    def collect_mmf(self):
        for rec in self.search([('state', 'in', ['confirm', 'send', 'valid'])]):
            rec.action_done()


class MonthlyManagementFeeLine(models.Model):
    _name = 'tt.monthly.fee.line'
    # _inherit = 'tt.history'
    _order = 'id desc'
    _description = 'Monthly Fee Line'

    mmf_id = fields.Many2one('tt.monthly.fee', 'Monthly Management Fee', ondelete='cascade')
    ledger_id = fields.Many2one('tt.ledger', 'Ledger', readonly=True, states={'draft':[('readonly',False)]})
    date = fields.Date('Date', help='Ledger Date')
    res_model = fields.Char('Related Reservation Model', index=True)
    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource')
    resv_name = fields.Char('Reservation Name')
    transaction_type = fields.Char('Transaction Type')
    pnr = fields.Char('PNR')
    carrier_name = fields.Char("Carrier", readonly=True, states={'draft':[('readonly',False)]})
    agent_name = fields.Char("Agent", readonly=True, states={'draft':[('readonly',False)]})
    # contact_id = fields.Many2one('tt.customer', 'Contact', readonly=True, states={'draft':[('readonly',False)]})
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('send', 'Send'),
                              ('valid', 'Validate'), ('recheck', 'Re-Check'), ('done', 'Done')], string='State',
                             related='mmf_id.state')

    amount = fields.Float('Amount', compute='get_ledger_value', readonly=True, states={'draft':[('readonly',False)]})
    is_checked = fields.Boolean('Apply')
    description = fields.Text('Description')

    def get_contact_id(self):
        for rec in self:
            resv_obj = self.env[rec.ledger_id.res_model].browse(rec.ledger_id.res_id)
            rec.contact_id = resv_obj.booker_id.id
            rec.carrier_name = resv_obj.carrier_name

    @api.onchange('ledger_id')
    @api.depends('ledger_id')
    def get_ledger_value(self):
        for rec in self:
            rec.amount = rec.ledger_id.sudo().debit - rec.ledger_id.sudo().credit
