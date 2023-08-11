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
        if self.env.user.has_group('base.group_erp_manager'):
            search_param = []
        elif self.env.user.ho_id:
            search_param = [('ho_id', '=', self.env.user.ho_id.id)]
        else:
            search_param = [('id', '=', -1)]
        provider_type = self.env['tt.agent.type'].search(search_param)
        for rec in provider_type:
            temp_dict = (rec.code, rec.name)
            if not temp_dict in value:
                value.append(temp_dict)
        return value
