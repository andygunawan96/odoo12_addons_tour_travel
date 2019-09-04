from odoo import api,models,fields
from odoo import exceptions

class TtPaymentInvoiceRel(models.Model):
    _name = 'tt.payment.invoice.rel'
    _description = 'Rodex Model'

    invoice_id = fields.Many2one('tt.agent.invoice', 'Invoice')
    payment_id = fields.Many2one('tt.payment', 'Payment', required=True, domain=[('available_amount','>',0),('state','=','validated')])
    pay_amount = fields.Monetary('Pay Amount', required=True)
    available_amount = fields.Monetary('Available Ammount', related="payment_id.available_amount")
    currency_id = fields.Many2one('res.currency', 'currency', related="payment_id.currency_id")
    state = fields.Selection('State',related='payment_id.state')

    @api.model
    def create(self, vals_list):
        print(vals_list)
        if vals_list.get('pay_amount') == 0:
            raise exceptions.UserError("Pay amount cannot be 0")
        payment_obj = self.env['tt.payment'].sudo().browse(vals_list.get('payment_id'))
        invoice_obj = self.env['tt.agent.invoice'].sudo().browse(vals_list.get('invoice_id'))

        #pengecekan overpaid
        missing_ammount = invoice_obj.total - invoice_obj.paid_amount
        if payment_obj.available_amount >= missing_ammount and vals_list['pay_amount'] > missing_ammount:
            vals_list['pay_amount'] = missing_ammount

        if vals_list['pay_amount'] > payment_obj.available_amount:
            raise exceptions.UserError("Pay amount on %s exceeded payment's residual amount" % (invoice_obj.name))

        if payment_obj.available_amount >= vals_list.get('pay_amount'):
            new_rel = super(TtPaymentInvoiceRel, self).create(vals_list)
            # payment_obj.calculate_amount()
            # new_rel.invoice_id.calculate_paid_amount()
            # self._cr.commit()
            return new_rel
        else:
            raise exceptions.UserError('Payment not enough to pay nominal amount. Please choose another payment or reduce tha pay amount')

    @api.onchange('pay_amount')
    def pay_amount_validator(self):
        if not self.payment_id and self.pay_amount != 0:
            raise exceptions.UserError("Please select payment first")

        if self.invoice_id:
            # pengecekan overpaid
            missing_ammount = self.invoice_id.total - self.invoice_id.paid_amount
            if self.payment_id.available_amount >= missing_ammount and self.pay_amount > missing_ammount:
                self.pay_amount = missing_ammount
                # raise exceptions.UserError("Pay amount c8hanged to missing amount")




class TtPaymentInh(models.Model):
    _inherit = 'tt.payment'

    invoice_ids = fields.One2many('tt.payment.invoice.rel', 'payment_id', 'Invoices',readonly=True)

    @api.multi
    @api.depends('invoice_ids.pay_amount','total_amount','fee')
    def compute_available_amount(self):
        for rec in self:
            super(TtPaymentInh, rec).compute_available_amount()
            used_amount = 0
            for inv in rec.invoice_ids:
                if inv.create_date:
                    used_amount += inv.pay_amount
                # used_amount += inv.pay_amount
            rec.used_amount = used_amount
            rec.available_amount -= rec.used_amount

            print(rec.used_amount)
            print(rec.available_amount)
            if rec.available_amount < 0:
                raise exceptions.UserError("Pay amount on %s exceeded payment's residual amount" % (self.name))


