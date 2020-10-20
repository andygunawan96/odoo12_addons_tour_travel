from odoo import models, fields, api

class TtAgentReportBalanceLog(models.Model):
    _name = 'tt.agent.report.balance.log'

    file = fields.Binary('File')
