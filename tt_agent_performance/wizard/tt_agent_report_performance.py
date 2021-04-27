from odoo import api, fields, models

AGENT_TYPE = [
    ('all', 'All'),
    ('japro', 'Japro'),
    ('citra', 'Citra'),
    ('btbo', 'BTBO')
]

class AgentReportPerformance(models.TransientModel):
    _name = 'tt.agent.report.performance.wizard'
    _inherit = 'tt.agent.report.common.wizard'

    state = fields.Selection([('a', 'a')], default='a')
    agent_type = fields.Selection(selection=lambda self: self._compute_provider_type_selection(),
                                     string='Agent Type', default='all')
    # agent_type = fields.Many2one('tt.agent.type', 'Agent Type')

    def _compute_provider_type_selection(self):
        value = [('all', 'All')]
        provider_type = self.env['tt.agent.type'].search([])
        for rec in provider_type:
            temp_dict = (rec.code, rec.name)
            if not temp_dict in value:
                value.append(temp_dict)
        return value