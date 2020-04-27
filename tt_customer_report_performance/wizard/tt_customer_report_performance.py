from odoo import api, fields, models

class CustomerReportPerformance(models.TransientModel):
    _name = 'tt.customer.report.performance.wizard'
    _inherit = "tt.agent.report.common.wizard"

    state = fields.Selection([('a', 'a')], default='a')
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