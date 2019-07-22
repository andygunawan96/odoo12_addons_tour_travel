from odoo import models, fields, api, _


class AgentRegistrationCustomer(models.Model):
    _inherit = 'tt.customer'

    agent_registration_id = fields.Many2one('tt.agent.registration', 'Agent Registration ID')
