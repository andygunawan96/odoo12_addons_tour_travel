from odoo import api,models,fields

class TtProviderTypeInh(models.Model):
    _inherit = 'tt.provider.type'

    @api.model
    def create(self, vals_list):
        new_p_type = super(TtProviderTypeInh, self).create(vals_list)
        self.env['tt.adjustment.type'].create({
            'name': new_p_type.name,
            'code': new_p_type.code,
            'provider_type_id': new_p_type.id
        })
        return new_p_type