from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MergeInvoice(models.Model):
    _name = "tt.merge.invoice.wizard"
    _description = 'Rodex Model'

    current_invoice_name = fields.Char('Current Invoice Name', related="current_invoice_line.name", readonly=True)
    current_invoice_line = fields.Many2one('tt.agent.invoice.line', 'Current Invoice Line')
    dummy_target_invoice = fields.Boolean('Generate Available Target Invoice(s)')

    def get_target_invoice_domain(self):
        return [('id', '!=', self.current_invoice_line.id), ('reference', '=', self.current_invoice_line.reference)]

    target_invoice_line = fields.Many2one('tt.agent.invoice.line', 'Target Invoice Line', required=True, domain=[('id', '=', -1)])

    res_model_resv = fields.Char('Related Document Name')
    res_id_resv = fields.Integer('Related Document ID')

    invoice_id = fields.Many2one('tt.agent.invoice', 'Invoice ID')

    invoice_line_detail_list = fields.One2many('tt.merge.invoice.line', 'merge_wizard_id', ondelete='cascade')

    @api.depends('current_invoice_line', 'dummy_target_invoice')
    @api.onchange('current_invoice_line', 'dummy_target_invoice')
    def _onchange_domain_target_invoice(self):
        return {'domain': {
            'target_invoice_line': self.get_target_invoice_domain()
        }}

    def get_form_id(self):
        return self.env.ref("tt_agent_sales.tt_merge_invoice_wizard_form_view")

    def perform_merge(self):
        if (self.target_invoice_line.id == self.current_invoice_line.id) or (self.target_invoice_line.reference != self.current_invoice_line.reference):
            raise UserError("Target Invoice Line is not compatible. Please choose a Target Invoice Line that has the same reference with Current Invoice Line!")

        for rec in self.invoice_line_detail_list:
            rec.invoice_line_detail_id.write({
                'invoice_line_id': self.target_invoice_line.id
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


