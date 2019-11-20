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
