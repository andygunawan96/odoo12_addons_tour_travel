from odoo import models, fields, api


class ResEmployee(models.Model):
    _name = 'res.employee'
    _rec_name = 'name'
    _description = 'Tour & Travel - Res Employee'

    name = fields.Char('Name', required=True)
    active = fields.Boolean(string="Active",default=True)
    customer_id = fields.Many2one('tt.customer', 'Customer')
    company_id = fields.Many2one('tt.company', string='Company')
    job = fields.Char('Job')
    job_title = fields.Char('Job Title')
