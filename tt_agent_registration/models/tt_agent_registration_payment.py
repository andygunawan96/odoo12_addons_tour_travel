from odoo import models, fields, api

STATE = [
    ('draft', 'Draft'),
    ('sent', 'Sent'),
    ('late', 'Late'),
    ('paid', 'Paid'),
    ('cancel', 'Cancel')
]

PAYMENT_TYPE = [
    ('balance', 'Balance'),
    ('other', 'Other')
]


class AgentRegistrationPayment(models.Model):
    _name = 'tt.agent.registration.payment'
    _description = 'Rodex Model'

    state = fields.Selection(STATE, 'State', default='draft')
    agent_registration_id = fields.Many2one('tt.agent.registration', 'Request')
    amount = fields.Monetary('Amount', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_type = fields.Selection(PAYMENT_TYPE, 'Method')
    percentage = fields.Float('Percentage')
    description = fields.Text('Description')
    due_date = fields.Datetime('Due Date')
    schedule_date = fields.Datetime('Schedule Date')

    @api.onchange('percentage')
    @api.depends('percentage')
    def compute_amount(self):
        for rec in self.agent_registration_id.payment_ids:
            rec.amount = rec.agent_registration_id.total_fee * rec.percentage / 100

    @api.model
    def _cron_check_payment(self):
        late_payments = self.search([('due_date', '<', fields.Datetime.now()), ('state', '!=', 'paid')])
        paid_payments = self.search([('due_date', '<', fields.Datetime.now()), ('state', '=', 'paid')])
        for rec in late_payments:
            rec.state = 'late'
        for rec in paid_payments:
            # Create agent invoice
            pass
