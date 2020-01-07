from odoo import api,models,fields
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
from ...tools import variables


class Ledger(models.Model):
    _inherit = 'tt.ledger'

    reschedule_id = fields.Many2one('tt.reschedule', 'After Sales')


class TtReschedule(models.Model):
    _name = "tt.reschedule"
    _inherit = "tt.refund"
    _description = "After Sales Model"
    _order = 'id DESC'

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('sent', 'Sent'), ('validate', 'Validated'), ('approve', 'Approved'),
                              ('done', 'Done'), ('cancel', 'Canceled'), ('expired', 'Expired')], 'Status',
                             default='draft',
                             help=" * The 'Draft' status is used for Agent to make after sales request.\n"
                                  " * The 'Confirmed' status is used for HO to confirm and process the request.\n"
                                  " * The 'Sent' status is used for HO to send the request back to Agent with a set price.\n"
                                  " * The 'Validated' status is used for Agent to final check and validate the request.\n"
                                  " * The 'Approved' status is used for HO to approve and process the request.\n"
                                  " * The 'Done' status means the agent's request has been done.\n"
                                  " * The 'Canceled' status is used for Agent or HO to cancel the request.\n"
                                  " * The 'Expired' status means the request has been expired.\n")
    ledger_ids = fields.One2many('tt.ledger', 'reschedule_id', 'Ledger(s)')
    reschedule_amount = fields.Integer('Expected After Sales Amount', default=0, required=True, readonly=True, related='reschedule_amount_ho')
    real_reschedule_amount = fields.Integer('Real After Sales Amount from Vendor', default=0, required=True, readonly=False, states={'done': [('readonly', True)], 'approve': [('readonly', True)], 'draft': [('readonly', True)]})
    reschedule_amount_ho = fields.Integer('Expected After Sales Amount', default=0, required=True, readonly=True, states={'confirm': [('readonly', False)]})
    new_pnr = fields.Char('New PNR', readonly=True, compute="_compute_new_pnr")
    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=','tt.reschedule')])
    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')
    old_segment_ids = fields.Many2many('tt.segment.airline', 'tt_reschedule_old_segment_rel', 'reschedule_id', 'segment_id', string='Old Segments',
                                      readonly=True)
    new_segment_ids = fields.Many2many('tt.segment.reschedule', 'tt_reschedule_new_segment_rel', 'reschedule_id', 'segment_id', string='New Segments',
                                  readonly=True, states={'draft': [('readonly', False)]})
    reschedule_type = fields.Selection([('reschedule', 'Reschedule'), ('revalidate', 'Revalidate'),
                                        ('reissued', 'Reissued'), ('upgrade', 'Upgrade Service'), ('addons', 'Addons (Meals, Baggage, Seat, etc)')], 'After Sales Type', default='reschedule',
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                       readonly=True)
    admin_fee_id = fields.Many2one('tt.master.admin.fee', 'Admin Fee Type', compute="")
    payment_acquirer_id = fields.Many2one('payment.acquirer', 'Payment Acquirer', domain="[('agent_id', '=', agent_id)]")

    @api.depends('invoice_line_ids')
    def set_agent_invoice_state(self):

        states = []

        for rec in self.invoice_line_ids:
            states.append(rec.state)

        if all(state == 'draft' for state in states) or not states:
            self.state_invoice = 'wait'
        elif all(state != 'draft' for state in states):
            self.state_invoice = 'full'
        elif any(state != 'draft' for state in states):
            self.state_invoice = 'partial'

    @api.depends('new_segment_ids')
    @api.onchange('new_segment_ids')
    def _compute_new_pnr(self):
        for rec in self:
            new_pnr = ''
            for rec2 in rec.new_segment_ids:
                new_pnr += rec2.pnr and rec2.pnr + ',' or ''
            rec.new_pnr = new_pnr and new_pnr[:-1] or ''

    @api.depends('admin_fee_id', 'reschedule_amount', 'res_model', 'res_id')
    @api.onchange('admin_fee_id', 'reschedule_amount', 'res_model', 'res_id')
    def _compute_admin_fee(self):
        for rec in self:
            if rec.admin_fee_id:
                if rec.admin_fee_id.type == 'amount':
                    pnr_amount = 0
                    book_obj = self.env[rec.res_model].browse(int(rec.res_id))
                    for rec2 in book_obj.provider_booking_ids:
                        pnr_amount += 1
                else:
                    pnr_amount = 1
                rec.admin_fee = rec.admin_fee_id.get_final_adm_fee(rec.reschedule_amount, pnr_amount)
            else:
                rec.admin_fee = 0

    @api.depends('admin_fee', 'reschedule_amount')
    @api.onchange('admin_fee', 'reschedule_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.reschedule_amount + rec.admin_fee

    def confirm_reschedule_from_button(self):
        if self.state != 'draft':
            raise UserError("Cannot Confirm because state is not 'draft'.")

        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
        })

    def send_reschedule_from_button(self):
        if self.state != 'confirm':
            raise UserError("Cannot Send because state is not 'confirm'.")

        self.write({
            'state': 'sent',
            'sent_uid': self.env.user.id,
            'sent_date': datetime.now(),
        })

    def validate_reschedule_from_button(self):
        if self.state != 'sent':
            raise UserError("Cannot Validate because state is not 'Sent'.")

        self.write({
            'state': 'validate',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now(),
            'final_admin_fee': self.admin_fee,
        })

    def approve_reschedule_from_button(self):
        if self.state != 'validate':
            raise UserError("Cannot Approve because state is not 'Validated'.")

        self.write({
            'state': 'approve',
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now()
        })

    def action_done(self):
        credit = self.reschedule_amount
        debit = 0
        if self.final_admin_fee:
            credit += self.final_admin_fee

        ledger_type = self.reschedule_type == 'addons' and 8 or 7

        self.env['tt.ledger'].create_ledger_vanilla(
            self.res_model,
            self.res_id,
            'Reschedule : %s' % (self.name),
            self.referenced_document,
            datetime.now() + relativedelta(hours=7),
            ledger_type,
            self.currency_id.id,
            self.env.user.id,
            self.agent_id.id,
            self.customer_parent_id.id,
            debit,
            credit,
            'Reschedule for %s' % (self.referenced_document),
            **{'reschedule_id': self.id}
        )

        self.action_create_invoice(credit)

        self.write({
            'state': 'done',
            'done_uid': self.env.user.id,
            'done_date': datetime.now()
        })

    def cancel_reschedule_from_button(self):
        if self.state in ['validate', 'approve']:
            if not self.cancel_message:
                raise UserError("Please fill the cancellation message!")
        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })

    def action_create_invoice(self, total_credit):
        invoice_id = False

        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': self.booker_id.id,
                'agent_id': self.agent_id.id,
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'state': 'confirm',
                'confirmed_uid': self.env.user.id,
                'confirmed_date': datetime.now()
            })

        desc_str = self.name + ' ('
        if self.referenced_document:
            desc_str += 'Reschedule for ' + self.referenced_document + ')'
        else:
            desc_str += ')'

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'desc': desc_str
        })

        invoice_line_id = inv_line_obj.id

        inv_line_obj.write({
            'invoice_line_detail_ids': [(0, 0, {
                'desc': desc_str,
                'price_unit': total_credit,
                'quantity': 1,
                'invoice_line_id': invoice_line_id,
            })]
        })

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create({
            'agent_id': self.agent_id.id,
            'acquirer_id': self.payment_acquirer_id and self.payment_acquirer_id.id or False,
            'real_total_amount': inv_line_obj.total,
            'customer_parent_id': self.customer_parent_id.id
        })

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': inv_line_obj.total,
        })

