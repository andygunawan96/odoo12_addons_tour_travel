from odoo import api,models,fields
from odoo import exceptions

class TtPaymentInvoiceRel(models.Model):
    _name = 'tt.payment.invoice.rel'
    _description = 'Rodex Model'

    invoice_id = fields.Many2one('tt.agent.invoice', 'Invoice')
    payment_id = fields.Many2one('tt.payment', 'Payment', required=True, domain=[('residual_amount','>',0),('state','=','validated')])
    pay_amount = fields.Monetary('Pay Amount', required=True)
    residual_amount = fields.Monetary('Residual Ammount', related="payment_id.residual_amount")
    currency_id = fields.Many2one('res.currency', 'currency', related="payment_id.currency_id")

    @api.model
    def create(self, vals_list):
        if vals_list.get('pay_amount') == 0:
            raise exceptions.UserError("Pay amount cannot be 0")
        payment_obj = self.env['tt.payment'].sudo().browse(vals_list.get('payment_id'))
        invoice_obj = self.env['tt.agent.invoice'].sudo().browse(vals_list.get('invoice_id'))

        #pengecekan overpaid
        missing_ammount = invoice_obj.total - invoice_obj.paid_amount
        if payment_obj.residual_amount >= missing_ammount and vals_list['pay_amount'] > missing_ammount:
            vals_list['pay_amount'] = missing_ammount

        if vals_list['pay_amount'] > payment_obj.residual_amount:
            raise exceptions.UserError("Pay amount on %s exceeded payment's residual amount" % (invoice_obj.name))

        print("ASDFSDF")
        if payment_obj.residual_amount >= vals_list.get('pay_amount'):
            new_rel = super(TtPaymentInvoiceRel, self).create(vals_list)
            payment_obj.calculate_amount()
            new_rel.invoice_id.calculate_paid_amount()
            self._cr.commit()
            return new_rel
        else:
            raise exceptions.UserError('Payment not enough to paid nominal amount. Please choose another payment or reduce tha pay amount')

    @api.onchange('pay_amount')
    def validate_pay_amount(self):
        if not self.payment_id and self.pay_amount != 0:
            raise exceptions.UserError("Please select payment first")


class TtPaymentInh(models.Model):
    _inherit = 'tt.payment'

    invoice_ids = fields.One2many('tt.payment.invoice.rel', 'payment_id', 'Invoices',readonly=True)

    def calculate_amount(self):
        used = 0
        for rec in self.invoice_ids:
            used += rec.pay_amount
        self.used_amount = used
        super(TtPaymentInh, self).calculate_amount()