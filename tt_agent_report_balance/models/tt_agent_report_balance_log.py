from odoo import models, fields, api

class TtAgentReportBalanceLog(models.Model):
    _name = 'tt.agent.report.balance.log'
    _description = 'Agent Report Balance Log'
    _order = 'id desc'

    name = fields.Char(string='File Name',default='agent_balance_report_log.xls')
    file = fields.Binary(string='File')
    date = fields.Date(string='Date')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
