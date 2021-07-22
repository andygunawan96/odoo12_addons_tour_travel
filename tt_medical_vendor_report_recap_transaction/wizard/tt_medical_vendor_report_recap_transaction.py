from odoo import fields, models, api
from ...tools import util,variables,ERR

STATES = [
    ('issued', 'Issued')
]

class AgentReportRecapReservation(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.medical.vendor.report.recap.transaction.wizard'

    state = fields.Selection(selection=STATES, string="State", default='issued')
    # statenya pasti issued
    state_vendor = fields.Selection(selection=lambda self: self._compute_state_vendor_selection(), string='State Vendor', default='verified')

    provider_type = fields.Selection(selection=lambda self: self._compute_provider_type_selection(),
                                     string='Provider Type', default='all', readonly=True)
    is_ho = fields.Boolean('Ho User', default=True)
    all_agent = fields.Boolean('All Agent', default=True, readonly=True)
    period_mode = fields.Selection(selection=[('issued_date', 'Issued Date'), ('verified_date', 'Verified Date'), ('test_date', 'Test Date')], string='Period Mode', default='issued_date')

    @api.onchange('period_mode')
    def _onchage_period_mode(self):
        if self.period_mode == 'verified_date':
            self.state_vendor = 'verified'

    def _compute_provider_type_selection(self):
        value = [('all', 'All')]
        provider_type = self.env['tt.provider.type'].search([])
        for rec in provider_type:
            temp_dict = (rec.code, rec.name)
            if not temp_dict in value:
                value.append(temp_dict)
        return value

    def _compute_state_vendor_selection(self):
        value = [('all', 'All')] + variables.STATE_VENDOR
        return value

    def _print_report(self, data):
        records = {
            'ids': self.ids,
            'model': self._name,
            'data_form': data['form']
        }
        return self.env.ref('tt_medical_vendor_report_recap_transaction.action_medical_vendor_report_recap_transaction').report_action(self, data=records)
