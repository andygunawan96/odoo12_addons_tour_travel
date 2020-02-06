from odoo import api,models,fields
from odoo import exceptions

class TtPaymentInvoiceRel(models.Model):
    _name = 'tt.payment.invoice.rel'
    _description = 'Rodex Model'

    invoice_id = fields.Many2one('tt.agent.invoice', 'Invoice')
    dummy_payment_field = fields.Boolean('Gen', default=False, help="Generate Payment List")

    def get_payment_domain(self):
        cust_par_id = self.invoice_id.customer_parent_id.id
        domain = [('available_amount','>',0),('state','=','approved'),('customer_parent_id', '=', cust_par_id)]
        return domain

    payment_id = fields.Many2one('tt.payment', 'Payment', required=True, domain=[('id', '=', -1)])
    pay_amount = fields.Monetary('Pay Amount', required=True)
    available_amount = fields.Monetary('Available Ammount', related="payment_id.available_amount")
    currency_id = fields.Many2one('res.currency', 'currency', related="payment_id.currency_id")
    state = fields.Selection('State',related='payment_id.state')
    payment_acquirer = fields.Char("Payment Acquirer", compute="_compute_payment_acquirer",store=True)

    @api.depends('invoice_id', 'dummy_payment_field')
    @api.onchange('invoice_id', 'dummy_payment_field')
    def _onchange_domain_payment(self):
        return {'domain': {
            'payment_id': self.get_payment_domain()
        }}

    @api.model
    def create(self, vals_list):
        print(vals_list)
        #comment 18jan 2020 krn tdk muncul raisenya di invoice tetapi tetap tidak terbuat
        # if vals_list.get('pay_amount') == 0:
        #     raise exceptions.UserError("Pay amount cannot be 0")
        payment_obj = self.env['tt.payment'].sudo().browse(vals_list.get('payment_id'))
        invoice_obj = self.env['tt.agent.invoice'].sudo().browse(vals_list.get('invoice_id'))

        #pengecekan overpaid
        missing_ammount = invoice_obj.total_after_tax - invoice_obj.paid_amount
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

    @api.multi
    def write(self, vals_list):
        vals_list.update({
            'dummy_payment_field': False
        })
        return super(TtPaymentInvoiceRel, self).write(vals_list)

    @api.depends('payment_id.acquirer_id.name')
    def _compute_payment_acquirer(self):
        for rec in self:
            if rec.payment_id:
                rec.payment_acquirer = rec.payment_id.acquirer_id.name

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
    def compute_available_amount(self):
        for rec in self:
            pass
            super(TtPaymentInh, rec).compute_available_amount()
            used_amount = 0
            for inv in rec.invoice_ids:
                if inv.create_date:
                    used_amount += inv.pay_amount
                # used_amount += inv.pay_amount
            print("inv used amount %d" %(used_amount))
            rec.used_amount += used_amount
            rec.available_amount -= used_amount

            print("used amount "+str(rec.used_amount))
            print("available amount "+str(rec.available_amount))
            # if rec.available_amount < 0:
            #     raise exceptions.UserError("Pay amount on %s exceeded payment's residual amount" % (self.name))

    def action_approve_payment(self):
        super(TtPaymentInh, self).action_approve_payment()
        for rec in self.invoice_ids:
            rec.invoice_id.check_paid_status()
            if rec.invoice_id.billing_statement_id:
                rec.invoice_id.billing_statement_id.check_status()
            if rec.invoice_id.customer_parent_type_id.id == self.env.ref('tt_base.customer_type_cor').id:
                rec.invoice_id.create_ledger(for_cor=1)
