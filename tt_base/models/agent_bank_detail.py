from odoo import models, fields, api


class AgentBankDetail(models.Model):
    _inherit = ['tt.history']
    _name = 'agent.bank.detail'
    _rec_name = 'account_number'
    _description = 'Tour & Travel - Agent Bank Detail'

    account_number = fields.Char('Account Number')
    account_holder_name = fields.Char('Account Holder Name')
    bank_id = fields.Many2one('tt.bank', 'Bank')

    def _get_ho_id_domain(self):
        return [('agent_type_id', '=', self.env.ref('tt_base.agent_type_ho').id)]

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=_get_ho_id_domain)
    agent_id = fields.Many2one('tt.agent', 'Agent')
    active = fields.Boolean('Active', default=True)
