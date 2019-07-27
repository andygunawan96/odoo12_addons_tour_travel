from odoo import api,models,fields

class AgentInvoiceLineDetail(models.Model):
    _name = "tt.agent.invoice.line.detail"
    _rec_name = 'desc'
    desc = fields.Text('Description')
    price_unit = fields.Float('Price')
    discount = fields.Float('Discount')
    quantity = fields.Integer('Quantity')
    discount_amount = fields.Float('Disc. Amount')
    price_subtotal = fields.Integer('Amount', compute = "_compute_amount_total")
    invoice_line_id = fields.Many2one('tt.agent.invoice.line', 'Invoice Line')

    @api.multi
    def _compute_amount_total(self):
        for rec in self:
            rec.price_subtotal = rec.quantity * rec.price_unit