from odoo import api, fields, models, _


class TtFrontendSecurity(models.Model):
    _name = 'tt.frontend.security'
    _description = 'Rodex Model'

    name = fields.Char('Name')
    code = fields.Char('Code')