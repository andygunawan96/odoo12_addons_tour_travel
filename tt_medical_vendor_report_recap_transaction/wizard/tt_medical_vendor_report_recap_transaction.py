from odoo import fields, models, api

STATES = [
    ('issued', 'Issued')
]

class AgentReportRecapReservation(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.medical.vendor.report.recap.transaction.wizard'

    state = fields.Selection(selection=STATES, string="State", default='issued')
    # statenya pasti issued

    provider_type = fields.Selection(selection=lambda self: self._compute_provider_type_selection(),
                                     string='Provider Type', default='all', readonly=True)
    is_ho = fields.Boolean('Ho User', default=True)
    all_agent = fields.Boolean('All Agent', default=True, readonly=True)

    def _compute_provider_type_selection(self):
        value = [('all', 'All')]
        provider_type = self.env['tt.provider.type'].search([])
        for rec in provider_type:
            temp_dict = (rec.code, rec.name)
            if not temp_dict in value:
                value.append(temp_dict)
        return value

    def _print_report(self, data):
        records = {
            'ids': self.ids,
            'model': self._name,
            'data_form': data['form']
        }
        return self.env.ref('tt_medical_vendor_report_recap_transaction.action_medical_vendor_report_recap_transaction').report_action(self, data=records)