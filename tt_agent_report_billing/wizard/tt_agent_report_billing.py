from odoo import fields, models, api

STATE = [
    ('all', 'All'),
    ('draft', 'Draft'),
    ('confirm', 'Confirmed'),
    ('partial', 'Partial'),
    ('paid', 'Paid'),
    ('cancel', 'Cancelled')
         ]

class AgentReportBilling(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.agent.report.billing.wizard'

    state = fields.Selection(selection=STATE, string="State", default='all')

    def _print_report(self, data):
        records = {
            'ids': self.ids,
            'model': self._name,
            'data_form': data['form']
        }
        return self.env.ref('tt_agent_report_invoice.action_agent_report_invoice').report_action(self, data=records)
