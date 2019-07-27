from odoo import models,api,fields
from ...tools import test_to_dict


class AgentInvoice(models.Model,test_to_dict.ToDict):

    _name = 'tt.agent.invoice.line'
    _rec_name = 'name'

    name = fields.Char('Name')
    name_inv = fields.Char('Name',related="invoice_id.name")

    total = fields.Integer('Total',compute='_compute_total')

    res_model_resv = fields.Char(
        'Related Reservation Name', required=True, index=True)
    res_id_resv = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource')

    model_type_id = fields.Many2one('tt.provider.type', 'Reservation Type')

    invoice_id = fields.Many2one('tt.agent.invoice','Invoice', ondelete='cascade')

    state = fields.Selection([],'State',related="invoice_id.state", readonly=True)

    invoice_line_detail_ids = fields.One2many('tt.agent.invoice.line.detail', 'invoice_line_id', 'Invoice Line Detail')

    desc = fields.Text('Description')

    def create(self, vals_list):
        if 'name' not in vals_list:
            vals_list['name'] = self.env['ir.sequence'].next_by_code('agent.invoice.line')

        new_invoice_line = super(AgentInvoice, self).create(vals_list)

        new_invoice_line_obj = new_invoice_line.get_reservation_obj()

        if 'provider_type_id' in new_invoice_line_obj:
            new_invoice_line.model_type_id = new_invoice_line_obj.provider_type_id.id
        elif 'provider_type' in new_invoice_line_obj:
            new_invoice_line.model_type_id = new_invoice_line_obj.provider_type.id

        return new_invoice_line

    @api.multi
    def _compute_total(self):
        for rec in self:
            total = 0
            for detail in rec.invoice_line_detail_ids:
                total += detail.price_subtotal
            rec.total = total

    def get_reservation_obj(self):
        return self.env[self.res_model_resv].browse(self.res_id_resv)

    def open_reservation(self):
        form_id = self.env[self.res_model_resv].get_form_id()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model_resv,
            'res_id': self.res_id_resv,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def open_split_wizard(self):
        wizard_obj = self.env['tt.split.invoice.wizard'].create({
            'current_invoice_line': self.id,
            'invoice_id': self.invoice_id.id,
            'split_count': 2,
            'res_model_resv': self.res_model_resv,
            'res_id_resv': self.res_id_resv
        })

        detail_ids = self.invoice_line_detail_ids.ids
        lines = [self.env['tt.split.invoice.line'].sudo().create({
            'invoice_line_detail_id': p,
            'limit': 2,
            'new_invoice_number': 18,
            'split_wizard_id': wizard_obj.id,
        }).id for p in detail_ids]

        form_id = self.env['tt.split.invoice.wizard'].get_form_id()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Split Wizard',
            'res_model': 'tt.split.invoice.wizard',
            'res_id': wizard_obj.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'new',
        }