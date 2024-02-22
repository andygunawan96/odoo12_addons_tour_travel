from odoo import fields, models, api, _
import werkzeug
from odoo.exceptions import UserError
from datetime import datetime
import logging, traceback
import pytz
_logger = logging.getLogger(__name__)


class AgentInvoice(models.Model):
    _inherit = 'tt.agent.invoice'

    billing_statement_id = fields.Many2one('tt.billing.statement', 'Billing Statement', ondelete="set null")
    billing_date = fields.Date('Billing Date', related='billing_statement_id.date_billing', store=True)
    billing_uid = fields.Many2one('res.users', 'Billed by')

    def check_paid_status(self):
        super(AgentInvoice, self).check_paid_status()
        if self.prev_state != self.state: ## kalau state tidak burubah jangan create ledger
            if self.state == 'paid':
                if self.customer_parent_type_id.id in [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id] and not self.customer_parent_id.check_use_ext_credit_limit():
                    self.create_ledger_invoice(debit=True)
            elif self.state == 'bill2':
                if self.customer_parent_type_id.id in [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id] and not self.customer_parent_id.check_use_ext_credit_limit():
                    self.create_ledger_invoice(debit=False)
        if self.billing_statement_id:
            self.billing_statement_id.check_status_bs()

    def _unlink_ledger(self):
        for rec in self:
            rec.ledger_id.sudo().unlink()

    # MOVED TO ACTION_CANCEL ON TT_AGENT_SALES/MODELS/TT_AGENT_INVOICE.PY
    @api.one
    def action_set_to_confirm(self):
        #untuk keluarkan agent_invoice dari tt.billing.statemet-invoice.ids
        if self.billing_statement_id:
            if self.billing_statement_id.state == 'paid':
                raise UserError(_("You cannot change the state to 'Confirm' which Billing Statement's state is PAID"))
            add_notes = 'Ex- Agent Invoice : %s' % self.name
            self.billing_statement_id.notes = self.billing_statement_id.notes and self.billing_statement_id.notes + '\n' + add_notes or add_notes

        self.update({
            'billing_statement_id': False,
            'state': 'confirm',
        })
        # self._unlink_ledger()

    #manual
    def action_bill(self):
        # security : user_agent_supervisor
        if self.state != 'confirm':
            raise UserError('You can only create Bill Statement from an invoice that has been set to \'Confirm\'.')
        ledger_diff = 0
        for ledger_obj in self.ledger_ids:
            ledger_diff += ledger_obj.debit
            ledger_diff -= ledger_obj.credit
        if ledger_diff == 0:
            self.state = 'bill2'
            self.billing_uid = self.env.user.id
            self.create_ledger_invoice(debit=False)
        else:
            _logger.error("%s %s action_bill2 failed, because ledger exist" % (self.name, self.id))

    #cron
    def action_bill2(self):
        # security : user_agent_supervisor
        if self.state != 'confirm':
            raise UserError('You can only create Bill Statement from an invoice that has been set to \'Confirm\'.')
        ledger_diff = 0
        for ledger_obj in self.ledger_ids:
            ledger_diff += ledger_obj.debit
            ledger_diff -= ledger_obj.credit
        if ledger_diff == 0:
            self.state = 'bill2'
            self.billing_uid = self.env.user.id
            self.create_ledger_invoice(debit=False)
        else:
            _logger.error("%s %s action_bill2 failed, because ledger exist" % (self.name, self.id))

    def create_ledger_invoice(self, debit=False):
        # create_ledger dilakukan saat state = bill atau bill2
        # JIKA FPO : TIDAK BOLEH CREATE LEDGER
        # if self.contact_id.booker_type == 'FPO':
        #     return True
        # fixme ini mau di apain rulesnya
        # 1. pakai external ID corpor
        # 2. kalau agent_id dan customer_parent_type_id nya berbeda
        if self.customer_parent_type_id == self.env.ref('tt_base.customer_type_fpo'):
            return True

        amount = 0
        for rec in self.invoice_line_ids:
            amount += rec.total_after_tax

        self.env['tt.ledger'].create_ledger_vanilla(
            self._name,
            self.id,
            '%sAgent Invoice : %s' % ("Payment For " if debit else "",self.name),
            self.name,
            2,
            self.currency_id.id,
            self.env.user.id,
            False,
            self.customer_parent_id.id,
            amount if debit == True else 0,
            amount if debit == False else 0,
            'Ledger for: %s%s' % ("Payment " if debit else "",self.name),
            **{
                'agent_invoice_id': self.id
            }
        )

    def action_confirm(self):
        if self.state == 'draft':
            self.state = 'confirm'
            self.confirmed_date = fields.Datetime.now()
            self.confirmed_uid = self.env.user.id

    def create_billing_statement(self):
        if not self.env.user.has_group('tt_base.group_billing_statement_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 70')
        if any(rec.state != 'confirm' for rec in self):
            raise UserError(_('You cannot create Billing Statement that an Invoice has been set to \'Confirm\'.'))

        values = {
            # 'payment_term_id': self.payment_term_id.id,
            'due_date': fields.Date.context_today(self),
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'currency_id': self.currency_id.id,
            'contact_id': self.booker_id and self.booker_id .id or False,
            'invoice_ids': [(4, 0, self.ids)],
        }

        bill_obj = self.env['tt.billing.statement'].create(values)
        # bill_obj.onchange_sub_agent_id() #UPdate payment_term, due_date
        for rec in self:
            rec.update({
                'billing_statement_id': bill_obj.id,
            })
            # rec._onchange_payment_term_date_invoice()
            rec.action_bill()  #this call create_ledger for Agent Invoice
            rec.billing_statement_id.action_confirm()
