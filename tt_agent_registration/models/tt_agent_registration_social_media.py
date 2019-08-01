from odoo import api, fields, models


class AgentRegistrationSocialMedia(models.Model):
    _inherit = 'social.media.detail'

    agent_registration_id = fields.Many2one('tt.agent.registration', string='Agent Registration ID')