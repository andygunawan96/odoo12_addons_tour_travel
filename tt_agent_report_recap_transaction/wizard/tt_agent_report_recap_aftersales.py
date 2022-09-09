from odoo import fields, models, api


class AgentReportRecapAfterSales(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.agent.report.recap.aftersales.wizard'

    after_sales_type = fields.Selection(selection=[('all', 'All'), ('refund', 'Refund'), ('after_sales', 'After Sales')],
                                     string='After Sales Type', default='all')

    def _print_report(self, data):
        records = {
            'ids': self.ids,
            'model': self._name,
            'data_form': data['form']
        }
        return self.env.ref('tt_agent_report_recap_transaction.action_agent_report_recap_aftersales').report_action(self, data=records)
