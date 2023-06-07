from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SplitInvoice(models.Model):
    _name = "tt.split.invoice.wizard"
    _description = 'Split Invoice Wizard'

    # invoice_id1 = fields.Many2one('tt.agent.invoice','Source Invoice', readonly="1")
    # invoice_id2 = fields.Many2one('tt.agent.invoice','Target Invoice')

    current_invoice_name = fields.Char('Current Invoice Name', related="current_invoice_line.name", readonly=True)
    current_invoice_line = fields.Many2one('tt.agent.invoice.line', 'Current Invoice Line')

    split_count = fields.Integer('Split Count')

    res_model_resv = fields.Char('Related Document Name')
    res_id_resv = fields.Integer('Related Document ID')

    invoice_id = fields.Many2one('tt.agent.invoice', 'Invoice ID')

    # def default_passenger_list(self):
    #     p_list = self._context.get('passenger_ids')[0][2]
    #     print(len(p_list))
    #     lines = [self.env['tt.split.invoice.line'].sudo().create({'passenger_id': p,'limit': len(p_list)+1}).id for p in p_list]
    #     return [(6, 0, lines)]
    
    invoice_line_detail_list = fields.One2many('tt.split.invoice.line', 'split_wizard_id')

    def get_form_id(self):
        return self.env.ref("tt_agent_sales.tt_split_invoice_wizard_form_view")

    @api.onchange('split_count')
    @api.depends('split_count')
    def change_limit(self):
        if self.split_count > len(self.invoice_line_detail_list):
            self.split_count = len(self.invoice_line_detail_list)
        if self.split_count < 2:
            self.split_count = 2
        for rec in self.invoice_line_detail_list:
            rec.limit = self.split_count
            rec.modify_domain()

    def perform_split(self):
        ##fixme cek invoicenumber
        if self.split_count > len(self.invoice_line_detail_list) or self.split_count < 2:
            raise UserError("SPLIT COUNT MUST BE GREATER THAN 1 AND CANNOT BE HIGHER THAN PASSENGER COUNT.")

        num_list = []
        for rec in self.invoice_line_detail_list:
            if rec.new_invoice_number.name not in num_list:
                num_list.append(rec.new_invoice_number.name)

        if len(num_list) != self.split_count:
            raise UserError("The amount of New Invoice set does not match Split Count. (New Invoice Amount: %s, Split Count: %s)"%(len(num_list), self.split_count))

        invoice_line_list = []
        for idx,inv_count in enumerate(range(0,self.split_count)):
            temp_ho_obj = self.current_invoice_line.agent_id.get_ho_parent_agent()
            new_invoice = self.env['tt.agent.invoice.line'].create({
                'name': '%s%s' % (self.current_invoice_name, chr(idx + 97)),
                'res_model_resv': self.res_model_resv,
                'res_id_resv': self.res_id_resv,
                'reference': self.current_invoice_line.reference,
                'desc': self.current_invoice_line.desc,
                'invoice_id': self.invoice_id.id,
                'agent_id': self.current_invoice_line.agent_id.id,
                'ho_id': temp_ho_obj and temp_ho_obj.id or False
            })
            invoice_line_list.append(new_invoice)

            self.current_invoice_line.get_reservation_obj().write({
                'invoice_line_ids': [(4,new_invoice.id)]
            })
        
        for rec in self.invoice_line_detail_list:
            if (rec.new_invoice_number.name > self.split_count) or (0 >= rec.new_invoice_number.name):
                raise UserWarning("LIMIT REACHED")

            rec.invoice_line_detail_id.invoice_line_id = invoice_line_list[rec.new_invoice_number.name-1]

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
