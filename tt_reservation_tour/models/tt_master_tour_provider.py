from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime


class MasterTourProvider(models.Model):
    _name = 'tt.master.tour.provider'
    _rec_name = 'provider_id'
    _description = 'Master Tour Provider'

    provider_id = fields.Many2one('tt.provider', 'Provider', required=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', related='provider_id.provider_type_id',
                                       store=True, readonly=True)
    master_tour_id = fields.Many2one('tt.master.tour', 'Master Tour', readonly=True)
    quantity = fields.Integer('Quantity', required=True, default=1)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    total_price = fields.Monetary('Total Price', default=0)
    details = fields.Html('Details', default='')
    is_lg_required = fields.Boolean('Is LG Required', readonly=True, compute='compute_is_lg_required')
    letter_of_guarantee_ids = fields.One2many('tt.letter.guarantee', 'res_id', 'Letter of Guarantee(s)', readonly=True)

    @api.onchange('provider_id')
    def compute_is_lg_required(self):
        for rec in self:
            if rec.master_tour_id:
                if rec.master_tour_id.tour_code:
                    rec.is_lg_required = True if rec.provider_id.is_using_lg else False
                else:
                    rec.is_lg_required = False
            else:
                rec.is_lg_required = False

    def generate_lg(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_lg_po_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.')
        lg_exist = self.env['tt.letter.guarantee'].search([('res_model', '=', self._name), ('res_id', '=', self.id), ('type', '=', 'lg')])
        if lg_exist:
            raise UserError('Letter of Guarantee for this provider is already exist.')
        else:
            desc_str = self.master_tour_id.name + '<br/>'
            pax_desc_str = ''
            pax_amount = 0
            for rec in self.master_tour_id.passengers_ids:
                pax_amount += 1
                pax_desc_str += '%s. %s<br/>' % (rec.title, rec.name)
            price_per_mul = self.total_price / pax_amount / self.quantity
            lg_vals = {
                'res_model': self._name,
                'res_id': self.id,
                'provider_id': self.provider_id.id,
                'type': 'lg',
                'parent_ref': self.master_tour_id.name,
                'pax_description': pax_desc_str,
                'multiplier': 'Pax',
                'multiplier_amount': pax_amount,
                'quantity': 'Qty',
                'quantity_amount': self.quantity,
                'currency_id': self.currency_id.id,
                'price_per_mult': price_per_mul,
                'price': self.total_price,
            }
            new_lg_obj = self.env['tt.letter.guarantee'].create(lg_vals)
            line_vals = {
                'lg_id': new_lg_obj.id,
                'ref_number': self.master_tour_id.tour_code,
                'description': desc_str + self.details
            }
            self.env['tt.letter.guarantee.lines'].create(line_vals)
