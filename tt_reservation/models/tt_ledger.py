from odoo import api, models, fields


class tt_ledger(models.Model):
    _inherit = 'tt.ledger'

    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    res_model = fields.Char(
        'Related Reservation Name', index=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource')

    def open_reservation(self):
        try:
            form_id = self.env[self.res_model].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def prepare_vals_for_resv(self, resv_obj, vals):
        vals.update({
            'pnr': resv_obj.pnr,
            'date': fields.datetime.now(),
            'display_provider_name': resv_obj.provider_name,
            'provider_type_id': resv_obj.provider_type_id.id,
            'description': 'Ledger for ' + resv_obj.name,
            'res_id': resv_obj.id,
            'res_model': resv_obj._name,
            'issued_uid': resv_obj.sudo().issued_uid.id,
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
