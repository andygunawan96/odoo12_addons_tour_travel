from odoo import fields, models, api


class AgentReportLedger(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.agent.report.ledger.wizard'

    def _print_report(self, data):
        records = {
            'ids': self.ids,
            'model': self._name,
            'data_form': data['form']
        }
        return self.env.ref('tt_agent_report.action_agent_report_ledger').report_action(self, data=records)