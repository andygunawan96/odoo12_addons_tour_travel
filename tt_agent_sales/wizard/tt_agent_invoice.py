from odoo import api, fields, models, _
from datetime import datetime
#move invoice
class AgentInvoice(models.TransientModel):
    _name = "tt.agent.invoice.wizard"
    _description = 'Rodex Invoice Move Wizard Model'

    invoice_id1 = fields.Many2one('tt.agent.invoice','Source Invoice', readonly="1")

    @api.onchange("invoice_id1")
    @api.depends("invoice_id1")
    def _onchange_generate_inv_2_domain(self):
        return {'domain': {
            'invoice_id2': [('customer_parent_id','=',self.invoice_id1.customer_parent_id.id)]
        }}

    invoice_id2 = fields.Many2one('tt.agent.invoice','Target Invoice')

    invoice_line_ids = fields.Many2many('tt.agent.invoice.line','invoice_wizard_line_rel',
                                        'wizard_id','line_id','Invoice Line'
                                        ,domain="[('invoice_id','=',invoice_id1), ('total', '>', 0)]")

    def perform_move(self):
        if self.invoice_id2:
            target_invoice = self.invoice_id2
        else:
            temp_ho_obj = self.invoice_id1.agent_id.get_ho_parent_agent()
            target_invoice = self.invoice_id1.env['tt.agent.invoice'].create({
                'booker_id': self.invoice_id1.booker_id.id,
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                'agent_id': self.invoice_id1.agent_id.id,
                'customer_parent_id': self.invoice_id1.customer_parent_id.id,
                'customer_parent_type_id': self.invoice_id1.customer_parent_type_id.id,
                'state': 'confirm',
                'confirmed_uid': self.invoice_id1.confirmed_uid.id,
                'confirmed_date': datetime.now()
            })
        for rec in self.invoice_line_ids:
            rec.invoice_id = target_invoice.id

