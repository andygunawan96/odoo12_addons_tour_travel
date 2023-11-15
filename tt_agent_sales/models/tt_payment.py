from odoo import api,models,fields
from odoo import exceptions
from odoo.exceptions import UserError
from datetime import datetime
import pytz

class TtPaymentInvoiceRel(models.Model):
    _name = 'tt.payment.invoice.rel'
    _description = 'Payment Invoice Rel'

    invoice_id = fields.Many2one('tt.agent.invoice', 'Invoice', readonly="True")
    ho_invoice_id = fields.Many2one('tt.ho.invoice', 'HO Invoice', readonly="True")
    inv_customer_parent_id = fields.Many2one('tt.customer.parent','Invoice Customer Parent',related='invoice_id.customer_parent_id',store=True)
    # payment_id = fields.Many2one('tt.payment', 'Payment', required=True,
    #                              domain="[('is_full','=',False),('state','=','approved'),('customer_parent_id','!=',False),('customer_parent_id', '=', inv_customer_parent_id)]")
    payment_id = fields.Many2one('tt.payment', 'Payment', required=True,
                                 domain="[('is_full','=',False),('state','=','approved')]")

    payment_state = fields.Selection("Payment State",related="payment_id.state")
    pay_amount = fields.Monetary('Pay Amount', required=True)
    available_amount = fields.Monetary('Available Ammount', related="payment_id.available_amount")
    currency_id = fields.Many2one('res.currency', 'currency', related="payment_id.currency_id")
    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm'),
                              ('validated','Validated by Operator'),
                              ('validated2','Validated by Supervisor'),
                              ('approved','Approved'),
                              ('cancel','Cancelled')],'State',readonly=True)
    payment_acquirer = fields.Char("Payment Acquirer", compute="_compute_payment_acquirer",store=True)

    @api.model
    def create(self, vals_list):
        #comment 18jan 2020 krn tdk muncul raisenya di invoice tetapi tetap tidak terbuat
        # if vals_list.get('pay_amount') == 0:
        #     raise exceptions.UserError("Pay amount cannot be 0")

        vals_list['state'] = 'confirm'
        payment_obj = self.env['tt.payment'].sudo().browse(vals_list.get('payment_id'))
        invoice_obj = self.env['tt.agent.invoice'].sudo().browse(vals_list.get('invoice_id')) or self.env['tt.ho.invoice'].sudo().browse(vals_list.get('ho_invoice_id'))

        #pengecekan overpaid
        missing_ammount = invoice_obj.grand_total - invoice_obj.paid_amount
        if payment_obj.available_amount >= missing_ammount and vals_list['pay_amount'] > missing_ammount:
            vals_list['pay_amount'] = missing_ammount

        if vals_list['pay_amount'] > payment_obj.available_amount:
            raise exceptions.UserError("Pay amount on %s exceeded payment's residual amount" % (invoice_obj.name))
            # wizard_form = self.env.ref('tt_base.notification_pop_up_wizard_form_view', False)
            # vals = {
            #     'msg': "Pay amount on %s exceeded payment's residual amount" % (invoice_obj.name)
            # }
            # new_notif = self.env['notification.pop.up.wizard'].create(vals)
            # return {
            #     'name': ('Create Payment Relation Error'),
            #     'type': 'ir.actions.act_window',
            #     'res_model': 'notification.pop.up.wizard',
            #     'res_id': new_notif.id,
            #     'view_id': wizard_form.id,
            #     'view_type': 'form',
            #     'view_mode': 'form',
            #     'target': 'new'
            # }

        if payment_obj.available_amount >= vals_list.get('pay_amount'):
            new_rel = super(TtPaymentInvoiceRel, self).create(vals_list)
            # payment_obj.calculate_amount()
            # new_rel.invoice_id.calculate_paid_amount()
            # self._cr.commit()
            return new_rel
        else:
            raise exceptions.UserError('Payment not enough to pay nominal amount. Please choose another payment or reduce tha pay amount')

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
            missing_ammount = self.invoice_id.grand_total - self.invoice_id.paid_amount
            if self.payment_id.available_amount >= missing_ammount and self.pay_amount > missing_ammount:
                self.pay_amount = missing_ammount
                # raise exceptions.UserError("Pay amount changed to missing amount")

            if self.payment_id.available_amount < 0:
                raise exceptions.UserError("Pay amount exceeded available amount")

        if self.ho_invoice_id:
            # pengecekan overpaid
            missing_ammount = self.ho_invoice_id.grand_total - self.ho_invoice_id.paid_amount
            if self.payment_id.available_amount >= missing_ammount and self.pay_amount > missing_ammount:
                self.pay_amount = missing_ammount
                # raise exceptions.UserError("Pay amount changed to missing amount")

            if self.payment_id.available_amount < 0:
                raise exceptions.UserError("Pay amount exceeded available amount")

    def action_approve(self):
        if not ({self.env.ref('tt_base.group_payment_level_4').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 41')
        if self.pay_amount > self.payment_id.available_amount:
            raise exceptions.UserError("Cannot approve payment relation, pay amount exceeded payment's available amount.")
        self.write({
            'state': 'approved'
        })
        if self.invoice_id:
            self.invoice_id.check_paid_status()
        elif self.ho_invoice_id:
            self.ho_invoice_id.check_paid_status()
        self.payment_id.check_full()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_cancel(self):
        if not ({self.env.ref('tt_base.group_payment_level_4').id, self.env.ref('tt_base.group_tt_agent_finance').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 42')
        self.write({
            'state': 'cancel'
        })
        if self.invoice_id:
            self.invoice_id.check_paid_status()
        elif self.ho_invoice_id:
            self.ho_invoice_id.check_paid_status()
        self.payment_id.check_full()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def quick_approve(self):
        if not self.payment_id.reference:
            self.payment_id.reference = "Quick Approve by %s on %s" % (self.env.user.name,datetime.now(pytz.utc))
        self.payment_id.action_validate_from_button()
        self.payment_id.action_approve_from_button()

class TtPaymentInh(models.Model):
    _inherit = 'tt.payment'

    invoice_ids = fields.One2many('tt.payment.invoice.rel', 'payment_id', 'Invoices',readonly=True)
    is_ho_invoice_payment = fields.Boolean('Is HO Invoice Payment', readonly=True, compute='_compute_is_ho_invoice_payment', store=True)

    @api.depends('invoice_ids')
    @api.onchange('invoice_ids')
    def _compute_is_ho_invoice_payment(self):
        for rec in self:
            is_ho = False
            for inv in rec.invoice_ids:
                if inv.ho_invoice_id:
                    is_ho = True
            rec.is_ho_invoice_payment = is_ho

    def get_is_ho_invoice_payment(self):
        return self.is_ho_invoice_payment

    @api.multi
    def compute_available_amount(self):
        for rec in self:
            pass
            super(TtPaymentInh, rec).compute_available_amount()
            used_amount = 0
            for inv in rec.invoice_ids:
                if inv.create_date and inv.state == 'approved':
                    used_amount += inv.pay_amount
                # used_amount += inv.pay_amount
            rec.used_amount += used_amount
            rec.available_amount -= used_amount
            # if rec.available_amount < 0:
            #     raise exceptions.UserError("Pay amount on %s exceeded payment's residual amount" % (rec.name))

    def check_full(self):
        used_amount = 0
        for rec in self.invoice_ids:
            if rec.state == 'approved':
                used_amount += rec.pay_amount

        if used_amount >= self.real_total_amount:
            self.is_full = True
        else:
            self.is_full = False


    def action_approve_payment(self):
        super(TtPaymentInh, self).action_approve_payment()
        for rec in self.invoice_ids:
            if rec.state in ['cancel','confirm']:
                rec.action_approve()


    def action_cancel_from_button(self):
        super(TtPaymentInh, self).action_cancel_from_button()
        for rec in self.invoice_ids:
            rec.action_cancel()
