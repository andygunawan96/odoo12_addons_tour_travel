from odoo import fields, models, api

class ReportSelling(models.TransientModel):
    _inherit = 'tt.agent.report.common.wizard'
    _name = 'tt.report.selling.wizard'
    _description = "report for daily transaction"

    state = fields.Selection([('all', 'All')], default='all')

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

    def returning_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['departure'] == params['departure'] and dic['destination'] == params['destination']:
                return i
        return -1

    def returning_index_sector(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['departure'] == params['departure'] and dic['destination'] == params['destination'] and dic['sector'] == params['sector']:
                return i

        return -1

    def check_index(self, arr, key, param):
        for i, dic in enumerate(arr):
            if dic[key] == param:
                return i
        return -1

    def check_date_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['year'] == params['year'] and dic['month'] == params['month']:
                return i
        return -1

    def check_tour_route_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['category'] == params['category'] and dic['route'] == params['route']:
                return i
        return -1

    def check_offline_provider(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['provider_type'] == params['provider_type'] and dic['offline_provider_type'] == params['offline_provider_type']:
                return i
        return -1