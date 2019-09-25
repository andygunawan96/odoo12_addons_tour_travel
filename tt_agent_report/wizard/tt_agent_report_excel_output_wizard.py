from odoo import models, fields


class AgentReportExcelOutputWizard(models.TransientModel):
    _name = 'tt.agent.report.excel.output.wizard'
    _description = 'Wizard to store the Excel output'

    file_output = fields.Binary(string='Excel Output')
    name = fields.Char(string='File Name', help='Save report as .xls format', default='excel_report.xls')
