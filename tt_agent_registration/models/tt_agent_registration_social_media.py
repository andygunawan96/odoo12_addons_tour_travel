from odoo import models, fields


class AgentRegistrationSocialMedia(models.Model):
    _inherit = 'social.media.detail'

    agent_registration_id = fields.Many2one('tt.agent.registration', string='Agent Registration ID')
