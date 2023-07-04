from odoo import api, fields, models, _
from datetime import datetime


class CreateHOTransportCarrierSearchConfigWizard(models.TransientModel):
    _name = "create.ho.transport.carrier.search.config.wizard"
    _description = 'Create HO Transport Carrier Search Config Wizard'

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id)
    def _get_domain_default(self):
        return [('ho_id', '=', self.env.ref('tt_base.rodex_ho').id)]
    transport_carrier_search_ids = fields.Many2many('tt.transport.carrier.search', 'tt_transport_carrier_search_rel', 'ho_agent_id','transport_carrier_search_id',string='Transport Carrier Search', domain=_get_domain_default)

    def submit_create_carrier_search_config(self):
        if self.ho_id:
            ho_id = self.ho_id.id
        else:
            ho_id = self.env.user.agent_id.get_ho_parent_agent().id
        for rec in self.transport_carrier_search_ids:
            provider_ids = []
            for provider_obj in rec.provider_ids:
                provider_ids.append(provider_obj.id)
            self.env['tt.transport.carrier.search'].create({
                'name': rec.name,
                'carrier_id': rec.carrier_id.id,
                'provider_type_id': rec.provider_type_id.id,
                'is_default': rec.is_default,
                'ho_id': ho_id,
                'is_favorite': rec.is_favorite,
                'is_excluded_from_b2c': rec.is_excluded_from_b2c,
                'sequence': rec.sequence,
                'provider_ids': [(6, 0, provider_ids)],
                'active': rec.active,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
