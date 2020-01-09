from odoo import fields, models, api

class AgentReportBalance(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.agent.report.balance.wizard'

    state = fields.Selection([('a','a')], default='a')

    def get_allalala(self):
        return True
