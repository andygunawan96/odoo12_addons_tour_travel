from odoo import fields, models, api

STATES = [
    ('all', 'All'),
    ('booked', 'Booked'),
    ('issued', 'Issued'),
    ('expired', 'Expired'),
    ('others', 'Others')
]


class AgentReportRecapReservation(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.agent.report.recap.reservation.wizard'

    state = fields.Selection(selection=STATES, string="State", default='all')

    provider_type = fields.Selection(selection=lambda self: self._compute_provider_type_selection(),
                                     string='Provider Type', default='all')

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
        return self.env.ref('tt_agent_report_recap_reservation.action_agent_report_recap_reservation').report_action(self, data=records)
