from odoo import models, fields


class AgentRegistrationAddress(models.Model):
    _inherit = 'address.detail'

    agent_registration_id = fields.Many2one('tt.agent.registration', string='Agent Registration ID')
