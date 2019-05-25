from odoo import api, fields, models, _

class AgentInvoice(models.TransientModel):
    _name = "tt.agent.invoice.wizard"
    _description = ""

    invoice_id1 = fields.Many2one('tt.agent.invoice','Source Invoice', readonly="1")
    invoice_id2 = fields.Many2one('tt.agent.invoice','Target Invoice')

    invoice_line_ids = fields.Many2many('tt.agent.invoice.line','invoice_wizard_line_rel',
                                        'wizard_id','line_id','Invoice Line'
                                        ,domain="[('invoice_id','=',invoice_id1)]")


    def perform_move(self):
        if self.invoice_id2:
            target_invoice = self.invoice_id2
        else:
            target_invoice = self.env['tt.agent.invoice'].create({
                'name': 'New'
            })
        for rec in self.invoice_line_ids:
            rec.invoice_id = target_invoice.id

