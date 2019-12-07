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

    def apply_to_agent(self):
        for rec in self.env['res.users'].search([('agent_id','!=',self.env.ref('tt_base.rodex_ho').id)]):
            rec.write({
                'frontend_security_ids': [(4,self.id)]
            })

    def apply_to_HO(self):
        for rec in self.env['res.users'].search([('agent_id','=',self.env.ref('tt_base.rodex_ho').id)]):
            rec.write({
                'frontend_security_ids': [(4,self.id)]
            })
