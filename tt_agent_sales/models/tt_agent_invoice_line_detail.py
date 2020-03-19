from odoo import api,models,fields

class AgentInvoiceLineDetail(models.Model):
    _name = "tt.agent.invoice.line.detail"
    _rec_name = 'desc'
    _description = 'Rodex Model'

    desc = fields.Text('Description')
    price_unit = fields.Monetary('Price')
    quantity = fields.Integer('Quantity')
    price_subtotal = fields.Monetary('Amount', compute = "_compute_amount_total",store=True)
    invoice_line_id = fields.Many2one('tt.agent.invoice.line', 'Invoice Line')
    currency_id = fields.Many2one('res.currency','Currency',related='invoice_line_id.currency_id')


    @api.multi
    @api.depends('price_unit','quantity')
    def _compute_amount_total(self):
        for rec in self:
            rec.price_subtotal = rec.quantity * rec.price_unit