from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PaymentRules(models.Model):
    _name = 'tt.payment.rules'
    _order = 'due_date'
    _description = 'Payment Rules'

    name = fields.Char('Name', required=True, default='Full Payment')
    description = fields.Char('Description')
    payment_percentage = fields.Float('Payment Percentage (%)', default=0, required=True)
    due_date = fields.Date('Due Date', required=True)
    pricelist_id = fields.Many2one('tt.master.tour', 'Tour Package ID', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('payment_percentage') and vals.get('pricelist_id'):
            total_percent = 0
            other_payment_rules = self.env['tt.payment.rules'].sudo().search([('pricelist_id', '=', vals['pricelist_id'])])
            for rec in other_payment_rules:
                total_percent += rec.payment_percentage
            tour_obj = self.env['tt.master.tour'].sudo().browse(int(vals['pricelist_id']))
            total_percent += tour_obj.down_payment
            if total_percent + vals['payment_percentage'] > 100.00:
                raise UserError(_('Total Installments and Down Payment cannot be more than 100%. Please re-adjust your Installment Payment Rules!'))
        return super(PaymentRules, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('payment_percentage'):
            total_percent = 0
            other_payment_rules = self.env['tt.payment.rules'].sudo().search([('pricelist_id', '=', self.pricelist_id.id), ('id', '!=', self.id)])
            for rec in other_payment_rules:
                total_percent += rec.payment_percentage
            total_percent += self.pricelist_id.down_payment
            if total_percent + vals['payment_percentage'] > 100.00:
                raise UserError(_('Total Installments and Down Payment cannot be more than 100%. Please re-adjust your Installment Payment Rules!'))
        return super(PaymentRules, self).write(vals)
