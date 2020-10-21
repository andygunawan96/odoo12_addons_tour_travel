from odoo import fields, models, api

class AgentReportBalance(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.agent.report.balance.wizard'

    state = fields.Selection([('a','a')], default='a')
    logging_daily = fields.Boolean('Logging Daily',default=False)

    def get_allalala(self):
        return True
