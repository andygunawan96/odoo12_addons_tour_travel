from odoo import models, fields, api

class TtCustomerParentReportBalanceLog(models.Model):
    _name = 'tt.customer.parent.report.balance.log'
    _description = 'Customer Parent Report Balance Log'
    _order = 'id desc'

    name = fields.Char(string='File Name',default='customer_parent_balance_report_log.xls')
    file = fields.Binary(string='File')
    date = fields.Date(string='Date')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    agent_id = fields.Many2one('tt.agent', 'Agent')
