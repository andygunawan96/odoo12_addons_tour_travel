from odoo import models,api,fields
from odoo.exceptions import UserError

class AgentInvoiceLineInh(models.Model):
    _name = 'tt.ho.invoice.line'
    _inherit = 'tt.agent.invoice.line'

    _rec_name = 'name'
    _description = 'HO Invoice Line'

    invoice_id = fields.Many2one('tt.ho.invoice', 'HO Invoice', ondelete='cascade')
    invoice_line_detail_ids = fields.One2many('tt.ho.invoice.line.detail', 'invoice_line_id', 'Invoice Line Detail')
    total_after_tax = fields.Monetary('Total (After Fee)', compute="_compute_total_tax", store=True) ## sama dengan agent invoice line hanya ganti tampilan

    @api.model
    def create(self, vals_list):
        # yang harusnya di pakai
        # if 'name' not in vals_list:
        #     vals_list['name'] = self.env['ir.sequence'].next_by_code('agent.invoice.line')

        ##utk debugging karena bisa jadi list val
        if type(vals_list) == dict:
            vals_list = [vals_list]
        for rec in vals_list:
            if 'name' not in rec:
                rec['name'] = self.env['ir.sequence'].next_by_code('ho.invoice.line')
        #####

        new_invoice_line = super(AgentInvoiceLineInh, self).create(vals_list)

        new_invoice_line_obj = new_invoice_line.get_reservation_obj()

        if 'provider_type_id' in new_invoice_line_obj:
            new_invoice_line.model_type_id = new_invoice_line_obj.provider_type_id.id
        elif 'provider_type' in new_invoice_line_obj:
            new_invoice_line.model_type_id = new_invoice_line_obj.provider_type.id

        return new_invoice_line

    @api.multi
    @api.depends('invoice_line_detail_ids.price_subtotal', 'invoice_line_detail_ids')
    def _compute_total(self):
        for rec in self:
            total = 0
            for detail in rec.invoice_line_detail_ids:
                if not detail.is_commission and not detail.is_point_reward:
                    total += detail.price_subtotal
                if detail.is_point_reward:
                    total -= detail.price_subtotal
            rec.total = total

    @api.multi
    @api.depends('total', 'discount')
    def _compute_total_tax(self):
        for rec in self:
            if rec.invoice_id.state == 'confirm' and rec.invoice_id.agent_id.tax_percentage:
                rec.total_after_tax = rec.total + ((rec.invoice_id.agent_id.tax_percentage / 100) * rec.total) - rec.discount
            else:
                rec.total_after_tax = rec.total - rec.discount