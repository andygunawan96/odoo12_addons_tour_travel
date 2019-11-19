from odoo import api, fields, models, _
from ...tools import variables

STATE_INVOICE = [
    ('open', 'Open'),
    ('trouble', 'Trouble'),
    ('done', 'Done'),
    ('cancel', 'Cancel')
]


# class tt_ledger(models.Model):
#     _inherit = 'tt.ledger'
#
#     resv_id = fields.Many2one('tt.reservation', 'Reservation ID', readonly=True)


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
