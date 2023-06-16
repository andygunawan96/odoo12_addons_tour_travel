from odoo import api, fields, models, _


class DynamicSelection(models.Model):
    _name = "tt.dynamic.selection"
    _description = 'Orbis Dynamic Selection Model'

    name = fields.Integer('value',required=True)


class SplitInvoiceLine(models.Model):
    _name = "tt.split.invoice.line"
    _description = 'Orbis Split Invoice Line Model'

    # passenger_id = fields.Many2one('tt.customer','Passenger')
    invoice_line_detail_id = fields.Many2one('tt.agent.invoice.line.detail', 'Invoice Line', readonly=True)
    limit = fields.Integer('Limit',default=2)
    split_wizard_id = fields.Many2one('tt.split.invoice.wizard', 'Split Wizard', ondelete='cascade')

    new_invoice_number = fields.Many2one('tt.dynamic.selection','New Invoice',domain="[('name','<=',limit)]")

    def modify_domain(self):
        return {'domain': {'new_invoice_number': [('name', '<=', self.limit)]}}
