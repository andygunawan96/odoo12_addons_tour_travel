from odoo import models,api,fields
from odoo.exceptions import UserError

class AgentInvoice(models.Model):

    _name = 'tt.agent.invoice.line'
    _rec_name = 'name'
    _description = 'Rodex Model'

    name = fields.Char('Name')

    total = fields.Integer('Total',compute='_compute_total', store=True)
    total_after_tax = fields.Integer('Total (After Tax)', compute="_compute_total_tax", store=True)

    res_model_resv = fields.Char(
        'Related Reservation Name', required=True, index=True)
    res_id_resv = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource')

    model_type_id = fields.Many2one('tt.provider.type', 'Reservation Type')

    invoice_id = fields.Many2one('tt.agent.invoice','Invoice', ondelete='cascade')

    state = fields.Selection([],'State',related="invoice_id.state", readonly=True)

    currency_id = fields.Many2one('res.currency', 'Currency', related='invoice_id.currency_id')

    invoice_line_detail_ids = fields.One2many('tt.agent.invoice.line.detail', 'invoice_line_id', 'Invoice Line Detail')

    desc = fields.Text('Description')

    reference = fields.Char('Reference')

    pnr = fields.Char("PNR",compute="_compute_invoice_line_pnr",store=True)

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
                rec['name'] = self.env['ir.sequence'].next_by_code('agent.invoice.line')
        #####

        new_invoice_line = super(AgentInvoice, self).create(vals_list)

        new_invoice_line_obj = new_invoice_line.get_reservation_obj()

        if 'provider_type_id' in new_invoice_line_obj:
            new_invoice_line.model_type_id = new_invoice_line_obj.provider_type_id.id
        elif 'provider_type' in new_invoice_line_obj:
            new_invoice_line.model_type_id = new_invoice_line_obj.provider_type.id

        return new_invoice_line

    def fill_reference(self):
        for rec in self.search([('reference','=',False)]):
            rec.reference = self.env[rec.res_model_resv].browse(rec.res_id_resv).name

    @api.multi
    @api.depends('invoice_line_detail_ids.price_subtotal')
    def _compute_total(self):
        for rec in self:
            total = 0
            for detail in rec.invoice_line_detail_ids:
                total += detail.price_subtotal
            rec.total = total

    @api.multi
    @api.depends("res_model_resv","res_id_resv")
    def _compute_invoice_line_pnr(self):
        for rec in self:
            if rec.res_model_resv and rec.res_id_resv:
                try:
                    rec.pnr = self.env[rec.res_model_resv].browse(rec.res_id_resv).pnr
                except:
                    pass

    def compute_pnr(self):
        for rec in self.search([]):
            rec._compute_invoice_line_pnr()

    @api.multi
    @api.depends('total')
    def _compute_total_tax(self):
        for rec in self:
            rec.total_after_tax = rec.total + ((rec.invoice_id.customer_parent_id.tax_percentage / 100) * rec.total)

    def get_reservation_obj(self):
        return self.env[self.res_model_resv].browse(self.res_id_resv)

    def open_reservation(self):
        try:
            form_id = self.env[self.res_model_resv].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model_resv)], limit=1)
            form_id = form_id[0] if form_id else False

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
        if not self.invoice_line_detail_ids or len(self.invoice_line_detail_ids.ids) < 2:
            raise UserError("Cannot split invoice line with less than 2 details.")

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