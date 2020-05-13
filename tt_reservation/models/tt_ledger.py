from odoo import api, models, fields


class tt_ledger(models.Model):
    _inherit = 'tt.ledger'

    def prepare_vals_for_resv(self, resv_obj,provider_pnr, vals,provider_name=False):
        vals.update({
            'pnr': provider_pnr,
            'date': fields.datetime.now(),
            'display_provider_name': provider_name or resv_obj.provider_name,
            'provider_type_id': resv_obj.provider_type_id.id,
            'description': 'Ledger for ' + resv_obj.name,
            'agent_id': vals.get('agent_id') or resv_obj.agent_id.id,
        })
        return vals

    # @api.model
    # def create(self, vals):
    #     if vals.get('res_model') and vals.get('res_id'):
    #         if 'provider_type_id' in vals:
    #             vals['provider_type_id'] = self.env[vals['res_model']].browse(vals['res_id']).provider_type_id.id
    #     return super(tt_ledger, self).create(vals)

    def get_allowed_list(self):
        a = super(tt_ledger, self).get_allowed_list()
        a.update({
            'pnr': (
                True,
                ('pnr',)
            )
        })
        return a
