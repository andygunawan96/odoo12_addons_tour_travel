from odoo import models, fields

class tt_ledger(models.Model):
    _inherit = 'tt.ledger'

    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    res_model = fields.Char(
        'Related Reservation Name', index=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource')

    def open_reservation(self):
        form_id = self.env[self.res_model].get_form_id()

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

    def create(self, vals_list):
        if 'res_model' in vals_list and 'res_id' in vals_list:
            vals_list['provider_type_id'] = self.env[vals_list['res_model']].browse(vals_list['res_id']).provider_type_id.id
        super(tt_ledger, self).create(vals_list)
