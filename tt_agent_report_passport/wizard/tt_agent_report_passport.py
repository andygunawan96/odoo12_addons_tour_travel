from odoo import fields, models, api


class AgentReportPassport(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.agent.report.passport.wizard'

    state = fields.Selection([('all', 'All'),
                              ('draft', 'Open'), ('confirm', 'Confirm to HO'), ('validate', 'Validated by HO'),
                              ('to_vendor', 'Send to Vendor'), ('vendor_process', 'Proceed by Vendor'),
                              ('cancel', 'Canceled'), ('payment', 'Payment'), ('in_process', 'In Process'),
                              ('partial_proceed', 'Partial Proceed'), ('proceed', 'Proceed'),
                              ('delivered', 'Delivered'), ('ready', 'Ready'), ('done', 'Done')],
                             'State', default='all')

    def _print_report(self, data):
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        return self.env.ref('tt_agent_report_passport.agent_report_passport_model').report_action(self, data=data)
