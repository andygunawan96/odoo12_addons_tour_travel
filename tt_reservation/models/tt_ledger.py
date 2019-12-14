from odoo import api, models, fields


class tt_ledger(models.Model):
    _inherit = 'tt.ledger'

    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')

    def prepare_vals_for_resv(self, resv_obj,provider_pnr, vals):
        vals.update({
            'pnr': provider_pnr,
            'date': fields.datetime.now(),
            'display_provider_name': resv_obj.provider_name,
            'provider_type_id': resv_obj.provider_type_id.id,
            'description': 'Ledger for ' + resv_obj.name,
            'agent_id': vals.get('agent_id') or resv_obj.agent_id.id,
        })
        return vals

    def reverse_ledger(self):
        reverse_id = self.env['tt.ledger'].create([{
            'name': 'Reverse:' + self.name,
            'debit': self.credit,
            'credit': self.debit,
            'ref': self.ref,
            'currency_id': self.currency_id.id,
            'transaction_type': self.transaction_type,
            'reverse_id': self.id,
            'agent_id': self.agent_id.id,
            'pnr': self.pnr,
            'issued_uid': self.issued_uid.id,
            'display_provider_name': self.display_provider_name,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'is_reversed': True,
            'description': 'Reverse for %s' % (self.name),
            'adjustment_id': self.adjustment_id and self.adjustment_id.id or False,
            'refund_id': self.refund_id and self.refund.id or False
        }])

        self.update({
            'reverse_id': reverse_id.id,
            'is_reversed': True,
        })

    @api.model
    def create(self, vals):
        if vals.get('res_model') and vals.get('res_id'):
            if 'provider_type_id' in vals:
                vals['provider_type_id'] = self.env[vals['res_model']].browse(vals['res_id']).provider_type_id.id
        return super(tt_ledger, self).create(vals)

    def get_allowed_list(self):
        a = super(tt_ledger, self).get_allowed_list()
        a.update({
            'pnr': ['pnr',]
        })
        return a
