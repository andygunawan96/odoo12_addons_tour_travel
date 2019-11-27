from odoo import api, fields, models, _
from ...tools import variables
from odoo.exceptions import UserError

STATE_INVOICE = [
    ('open', 'Open'),
    ('trouble', 'Trouble'),
    ('done', 'Done'),
    ('cancel', 'Cancel')
]


class InstallmentInvoice(models.Model):
    _name = 'tt.installment.invoice'
    _description = 'Rodex Model'

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    amount = fields.Monetary('Amount', default=0)

    due_date = fields.Date('Due Date', required=True)

    booking_id = fields.Many2one('tt.reservation.tour', 'Tour Reservation ID', readonly=True)
    tour_booking_state = fields.Selection(variables.BOOKING_STATE, related="booking_id.state", store=True)

    state_invoice = fields.Selection(STATE_INVOICE, 'State Invoice', default='open')

    # ledger_ids = fields.One2many('tt.ledger', 'resv_id', 'Ledger')
    agent_invoice_id = fields.Many2one('tt.agent.invoice', 'Agent Invoice')

    description = fields.Text('Description')
    payment_rules_id = fields.Many2one('tt.payment.rules', 'Payment Rules ID')

    def action_open(self):
        self.state_invoice = 'open'

    def action_trouble(self):
        self.state_invoice = 'trouble'

    def action_done(self):
        if self.agent_invoice_id.state == 'paid':
            self.state_invoice = 'done'
        else:
            raise UserError(
                _('Invoice has not been paid.'))

    def action_set_to_done(self):
        self.state_invoice = 'done'

    def action_cancel(self):
        if self.agent_invoice_id.state == 'cancel':
            self.state_invoice = 'cancel'
        else:
            raise UserError(
                _('Please cancel the invoice first.'))

    def action_pay_now(self):
        if self.state_invoice in ['open', 'trouble']:
            commission_ledger = False
            not_paid_installments = self.env['tt.installment.invoice'].sudo().search([('state_invoice', 'in', ['open', 'trouble']), ('booking_id', '=', int(self.booking_id.id)), ('id', '!=', int(self.id))])
            if not not_paid_installments:
                commission_ledger = True
            else:
                for rec in not_paid_installments:
                    if rec.due_date < self.due_date:
                        raise UserError(
                            _('Please pay the previous installment first!'))
            for rec in self.booking_id.provider_booking_ids:
                rec.action_create_installment_ledger(self.booking_id.issued_uid.id, self.payment_rules_id.id, commission_ledger)
            self.state_invoice = 'done'
        else:
            raise UserError(
                _('This installment cannot be paid.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
