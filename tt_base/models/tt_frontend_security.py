from odoo import api, fields, models, _


class TtFrontendSecurity(models.Model):
    _name = 'tt.frontend.security'
    _description = 'Rodex Model'

    name = fields.Char('Name')
    code = fields.Char('Code')

    def apply_to_all_user(self):
        for rec in self.env['res.users'].search([]):
            rec.write({
                'frontend_security_ids': [(4,self.id)]
            })