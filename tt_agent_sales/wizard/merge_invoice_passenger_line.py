from odoo import api, fields, models, _


class MergeInvoiceLine(models.Model):
    _name = "tt.merge.invoice.line"
    _description = 'Merge Invoice Line'

    invoice_line_detail_id = fields.Many2one('tt.agent.invoice.line.detail', 'Invoice Line', readonly=True)
    merge_wizard_id = fields.Many2one('tt.merge.invoice.wizard', 'Merge Wizard', ondelete='cascade')

