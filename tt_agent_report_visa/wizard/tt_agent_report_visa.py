from odoo import fields, models, api


class AgentReportVisa(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.agent.report.visa.wizard'

    state = fields.Selection([('all', 'All'),
                              ('draft', 'Open'), ('confirm', 'Confirm to HO'), ('validate', 'Validated by HO'),
                              ('to_vendor', 'Send to Vendor'), ('vendor_process', 'Proceed by Vendor'),
                              ('cancel', 'Canceled'), ('payment', 'Payment'), ('in_process', 'In Process'),
                              ('partial_proceed', 'Partial Proceed'), ('proceed', 'Proceed'),
                              ('delivered', 'Delivered'), ('ready', 'Ready'), ('done', 'Done')],
                             'State', default='all')

    def _print_report(self, data):
        records = {
            'ids': self.ids,
            'model': self._name,
            'data_form': data['form']
        }
        return self.env.ref('tt_agent_report_visa.action_agent_report_visa').report_action(self, data=records)
