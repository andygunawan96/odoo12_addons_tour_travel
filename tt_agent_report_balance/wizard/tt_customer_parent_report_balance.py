from odoo import fields, models, api

class CustomerParentReportBalance(models.TransientModel):
    _inherit = "tt.agent.report.common.wizard"
    _name = 'tt.customer.parent.report.balance.wizard'

    state = fields.Selection([('all','All')], default='all')
    logging_daily = fields.Boolean('Logging Daily',default=False)
