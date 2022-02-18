from odoo import api, fields, models, _
from odoo.exceptions import UserError
import math

class PaymentRules(models.Model):
    _name = 'tt.payment.rules.groupbooking'
    _description = 'Payment Rules'

    name = fields.Char('Name', required=True, default='Full Payment')
    description = fields.Char('Description')
    installment_ids = fields.One2many('tt.installment.groupbooking', 'payment_rules_id', string='Installment')

    active = fields.Boolean('Active', default=True)
    seq_id = fields.Char('Sequence ID', readonly=True)

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.payment.rules.groupbooking')
        payment_percentage = 0.0
        for rec in vals_list['installment_ids']:
            payment_percentage = payment_percentage + rec[2]['payment_percentage']
        if payment_percentage != 100:
            raise UserError(_('Total Installments have to be 100%. Please re-adjust your Installment Payment Rules!'))
        return super(PaymentRules, self).create(vals_list)


    def to_dict(self, currency, total_amount):
        installment = []
        for rec in self.installment_ids:
            installment.append(rec.to_dict(currency, total_amount))
        return{
            "name": self.name,
            "description": self.description,
            "payment_rules": installment,
            "payment_rules_seq_id": self.seq_id
        }
    #check total percentage di atas 100 % tidak

class InstallmentPayment(models.Model):
    _name = 'tt.installment.groupbooking'
    _order = 'due_date'
    _description = 'Payment Rules'

    payment_rules_id = fields.Many2one('tt.installment.groupbooking', 'Installment', ondelete='cascade')
    name = fields.Char('Name', required=True, default='Down Payment')
    description = fields.Char('Description')
    payment_percentage = fields.Float('Payment Percentage (%)', default=0, required=True)
    due_date = fields.Integer('Due Date in Day(s) after issued', required=True)

    def to_dict(self, currency, total_amount):
        return {
            "name": self.name,
            "description": self.description,
            "payment_percentage": self.payment_percentage,
            "due_date": self.due_date,
            "currency": currency,
            "amount": math.ceil(self.payment_percentage / 100 * total_amount)
        }