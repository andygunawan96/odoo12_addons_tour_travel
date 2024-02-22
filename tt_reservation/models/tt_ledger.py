from odoo import api, models, fields


class tt_ledger(models.Model):
    _inherit = 'tt.ledger'

    def prepare_vals_for_resv(self, resv_obj,provider_pnr, vals,provider_name=False):
        vals.update({
            'pnr': provider_pnr,
            'display_provider_name': provider_name or resv_obj.provider_name,
            'provider_type_id': resv_obj.provider_type_id.id,
            'description': 'Ledger for ' + resv_obj.name,
            'agent_id': vals.get('agent_id') or resv_obj.agent_id.id,
        })
        if not vals.get('ho_id'):
            if vals.get('agent_id'):
                agent_obj = self.env['tt.agent'].browse(int(vals['agent_id']))
                ho_obj = agent_obj and agent_obj.ho_id or False
            else:
                ho_obj = resv_obj.agent_id.ho_id
            if ho_obj:
                vals.update({
                    'ho_id': ho_obj.id
                })
        return vals

    # @api.model
    # def create(self, vals):
    #     if vals.get('res_model') and vals.get('res_id'):
    #         if 'provider_type_id' in vals:
    #             vals['provider_type_id'] = self.env[vals['res_model']].browse(vals['res_id']).provider_type_id.id
    #     return super(tt_ledger, self).create(vals)

    def get_allowed_rule(self):
        a = super(tt_ledger, self).get_allowed_rule()
        a.update({
            'pnr': (
                True,
                ('pnr',)## koma jangan di hapus nanti error tidak loop tupple tetapi string
            )
        })
        return a
