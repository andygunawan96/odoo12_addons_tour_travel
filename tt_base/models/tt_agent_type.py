from odoo import models, fields, api, _


class TtAgentType(models.Model):
    _name = 'tt.agent.type'
    _inherit = ['tt.history']
    _description = 'Tour & Travel - Agent Type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True, help='Fixed code, ex: citra, japro, for sale pricing', default='undefine')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('cancel', 'Cancelled')], string='State',
                             default='draft')
    active = fields.Boolean('Active', default='True')
    upline_ids = fields.Many2many('tt.agent.type', 'tt_agent_type_upline_1_2_rel', 'agent_1', 'agent_2')
    # upline_ids = fields.Many2many('tt.agent.type', 'tt_agent_type_upline_1_2_rel', 'agent_1', 'agent_2')
    description = fields.Text('Description')
    currency_id = fields.Many2one('res.currency', 'Currency')
    registration_fee = fields.Monetary('Registration Fee')
    min_monthly_fee = fields.Monetary('Min Monthly Fee')
    max_monthly_fee = fields.Monetary('Max Monthly Fee')
    percentage_monthly_fee = fields.Monetary('Percentage Monthly Fee')
    recruitment_fee = fields.Monetary('Recruitment Fee')
    registration_form = fields.Html(string="Registration Form")
    document = fields.Char(string="Document", required=False, )
    agent_ids = fields.One2many('tt.agent', 'agent_type_id', 'Agent')
    is_allow_regis = fields.Boolean('Allow Registration', default=False)
    commission_rule_ids = fields.One2many('tt.commission.rule', 'agent_type_id', 'Commission Rule(s)')
    recruitment_commission_ids = fields.One2many('tt.commission.rule', 'agent_type2_id',
                                                 'Recruitment Commission Rule(s)')

    # fixme : nanti akan diubah
    def calc_commission(self, amount, multiplier, carrier_id=False):
        rule_id = self.commission_rule_ids.filtered(lambda x: x.carrier_id.id == carrier_id or x.carrier_id.id == False)
        print(rule_id)
        if rule_id:
            rule_id = rule_id[0]
        else:
            return 0, 0, amount
        if rule_id.amount > 0:
            multiplier = rule_id.amount_multiplier == 'pppr' and multiplier or 1
            parent_commission = rule_id.amount * multiplier
            agent_commission = amount - parent_commission
            print('Amount : ' + str(amount))
            print('Parent Comm : ' + str(parent_commission))
            print('Agent Comm : ' + str(agent_commission))
        else:
            parent_commission = rule_id.parent_agent_amount * amount / 100
            agent_commission = rule_id.percentage * amount / 100
            print('Amount : ' + str(amount))
            print('Parent Comm : ' + str(parent_commission))
            print('Agent Comm : ' + str(agent_commission))

        ho_commission = amount - parent_commission - agent_commission
        print('HO Comm : ' + str(ho_commission))
        return agent_commission, parent_commission, ho_commission

    @api.multi
    def calc_recruitment_commission(self, agent_type_id, total_payment):
        comm_objs = self.recruitment_commission_ids.filtered(lambda x: x.rec_agent_type_id.id == agent_type_id.id)
        if comm_objs:
            return comm_objs[0].amount, comm_objs[0].parent_agent_amount, total_payment - comm_objs[0].amount - \
                   comm_objs[0].parent_agent_amount
        else:
            return 0, 0, total_payment


class CommissionRule(models.Model):
    _name = 'tt.commission.rule'

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type')
    agent_type2_id = fields.Many2one('tt.agent.type', 'Agent Type')
    rec_agent_type_id = fields.Many2one('tt.agent.type', 'Recruit By')
    carrier_id = fields.Many2one('tt.transport.carrier', 'Carrier', help='Set Empty for All Product Rule')
    carrier_code = fields.Char('Code', related='carrier_id.code')
    percentage = fields.Float('Commission (%)', default=100)
    amount = fields.Float('Amount')
    amount_multiplier = fields.Selection([('code', 'Booking Code'), ('pppr', 'Per Person Per Pax')],
                                         'Multiplier', help='Parent Agent Commision Type', default='code')
    parent_agent_type = fields.Selection([('per', 'Percentage'), ('amo', 'Amount')], 'Parent Type',
                                         help='Parent Agent Commision Type')
    parent_agent_amount = fields.Float('Parent Amount')
    ho_commission_type = fields.Selection([('per', 'Percentage'), ('amo', 'Amount')],
                                          'HO Commission Type', help='Head Office Commision Type')
    ho_amount = fields.Float('HO Amount')
    active = fields.Boolean('Active', default=True)

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
    #     return super(TtAgentType, self).write(value)
