from odoo import fields, models, api


class AgentReportOffline(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.agent.report.offline.wizard'

    state = fields.Selection([('all', 'All'), ('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('on_progress', 'On Progress'), ('paid', 'Paid'), ('posted', 'Done'),
                              ('refund', 'Refund'), ('expired', 'Expired'), ('cancel', 'Canceled')], 'State',
                             default='all')

    provider_type = fields.Selection(selection=lambda self: self._compute_provider_type_selection(),
                                     string='Provider Type', default='all')

    def _compute_provider_type_selection(self):
        value = [('all', 'All')]
        provider_type = self.env['tt.provider.type'].search([])
        for rec in provider_type:
            value.append((rec.code, rec.name))
        return value

    def _print_report(self, data):
        records = {
            'ids': self.ids,
            'model': self._name,
            'data_form': data['form']
        }
        return self.env.ref('tt_agent_report_offline.action_agent_report_offline').report_action(self, data=records)
