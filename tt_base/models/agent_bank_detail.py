from odoo import models, fields, api


class AgentBankDetail(models.Model):
    _inherit = ['tt.history']
    _name = 'agent.bank.detail'
    _rec_name = 'account_number'
    _description = 'Tour & Travel - Agent Bank Detail'

    active = fields.Boolean('Active', default=True)
    account_number = fields.Char('Account Number')
    account_holder_name = fields.Char('Account Holder Name')
    bank_id = fields.Many2one('tt.bank', 'Bank')
    agent_id = fields.Many2one('tt.agent', 'Agent')
