from odoo import api, fields, models, _

TOUR_BOOKING_STATE = [
    ('booked', 'Booked'),
    ('issued', 'Issued'),
    ('confirm', 'Confirm To HO'),
    ('confirmed', 'Confirm'),
    ('process', 'In Process'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled'),
    ('expired', 'Expired'),
    ('done', 'Done')
]

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

    tour_id = fields.Many2one('tt.reservation.tour', 'Tour ID', readonly=True)
    tour_booking_state = fields.Selection(TOUR_BOOKING_STATE, related="tour_id.state", store=True)

    state_invoice = fields.Selection(STATE_INVOICE, 'State Invoice', default='open')

    # ledger_ids = fields.One2many('tt.ledger', 'resv_id', 'Ledger')
    agent_invoice_id = fields.Many2one('tt.agent.invoice', 'Agent Invoice')

    description = fields.Text('Description')
