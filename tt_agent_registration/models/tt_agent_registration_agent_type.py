from odoo import models, fields


class AgentRegistrationAgentType(models.Model):
    _inherit = 'tt.agent.type'

    document_type_id = fields.Many2one('tt.document.type', 'Document Type')
    promotion_id = fields.Many2one('tt.agent.registration.promotion', 'Promotion')
