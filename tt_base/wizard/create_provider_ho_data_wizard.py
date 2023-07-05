from odoo import api, fields, models, _
from datetime import datetime


class CreateProviderHODataWizard(models.TransientModel):
    _name = "create.provider.ho.data.wizard"
    _description = 'Create Provider HO Data Wizard'

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id)
    is_using_balance = fields.Boolean('Is Using Balance')
    is_using_lg = fields.Boolean('Is Using Letter of Guarantee')
    is_using_po = fields.Boolean('Is Using Purchase Order')
    provider_ids = fields.Many2many('tt.provider', 'tt_create_provider_ho_wizard_provider_rel', 'create_provider_ho_id', 'provider_id', string='Provider(s)')

    def submit_create_provider_ho_data(self):
        if self.ho_id:
            ho_id = self.ho_id.id
        else:
            ho_id = self.env.user.agent_id.ho_id.id

        for rec in self.provider_ids:
            vals = {
                'is_using_balance': self.is_using_balance,
                'is_using_lg': self.is_using_lg,
                'is_using_po': self.is_using_po,
                'active': True
            }
            if rec.currency_id:
                vals.update({
                    'currency_id': rec.currency_id.id
                })
            existing_prov_ho = self.env['tt.provider.ho.data'].search([('provider_id', '=', rec.id), ('ho_id', '=', ho_id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
            if existing_prov_ho:
                existing_prov_ho[0].write(vals)
            else:
                vals.update({
                    'provider_id': rec.id,
                    'ho_id': ho_id,
                    'name': rec.name,
                })
                self.env['tt.provider.ho.data'].create(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
