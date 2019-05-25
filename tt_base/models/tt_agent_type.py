from odoo import models, fields, api, _


class TtAgentType(models.Model):
    _name = 'tt.agent.type'
    _inherit = ['tt.history']
    _description = 'Tour & Travel - Agent Type'

    name = fields.Char('Name', required=True)
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
    percentage_monthly_fee = fields.Float('Percentage Monthly Fee')
    recruitment_fee = fields.Monetary('Recruitment Fee')
    registration_form = fields.Html(string="Registration Form")
    document = fields.Char(string="Document", required=False, )
    agent_ids = fields.One2many('tt.agent', 'agent_type_id', 'Agent')
    history_ids = fields.Integer(string="History ID", required=False, )  # tt_history
    is_allow_regis = fields.Boolean('Allow Registration', default=False)

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
