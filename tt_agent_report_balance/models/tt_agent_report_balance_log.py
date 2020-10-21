from odoo import models, fields, api

class TtAgentReportBalanceLog(models.Model):
    _name = 'tt.agent.report.balance.log'

    name = fields.Char(string='File Name',default='agent_balance_report_log.xls')
    file = fields.Binary(string='File')
    date = fields.Date(string='Date')