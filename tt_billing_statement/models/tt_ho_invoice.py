from odoo import fields, models, api, _
import werkzeug
from odoo.exceptions import UserError
from datetime import datetime
import logging, traceback
import pytz
_logger = logging.getLogger(__name__)


class AgentInvoiceInh(models.Model):
    _inherit = 'tt.ho.invoice'

    billing_statement_id = fields.Many2one('tt.billing.statement', 'Billing Statement', ondelete="set null")
    billing_date = fields.Date('Billing Date', related='billing_statement_id.date_billing', store=True)
    billing_uid = fields.Many2one('res.users', 'Billed by')

    def check_paid_status(self):
        super(AgentInvoiceInh, self).check_paid_status()
        if self.prev_state != self.state: ## kalau state tidak burubah jangan create ledger
            if self.state == 'paid':
                # if self.customer_parent_type_id.id in [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id]:
                self.create_ledger_invoice(debit=True)
            elif self.state == 'bill2':
                # if self.customer_parent_type_id.id in [self.env.ref('tt_base.customer_type_cor').id, self.env.ref('tt_base.customer_type_por').id]:
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
        # if self.customer_parent_type_id == self.env.ref('tt_base.customer_type_fpo'):
        #     return True

        amount_list = [] ## untuk commission
        amount = 0
        total_amount = 0
        total_point_reward = 0
        book_obj = False
        ## ambil provider_type & provider
        provider_type_id = ''
        provider = ''
        for invoice_line_obj in self.invoice_line_ids:
            if provider_type_id == '' or provider == '':
                try:
                    book_obj = self.env[invoice_line_obj['res_model_resv']].browse(invoice_line_obj['res_id_resv'])
                    provider_type_id = book_obj.provider_type_id.id
                    provider = book_obj.provider_name
                    break
                except Exception as e:
                    _logger.error("%s, %s" % (str(e), traceback.format_exc()))


        for invoice_line_obj in self.invoice_line_ids:
            if not book_obj:
                book_obj = self.env[invoice_line_obj.res_model_resv].browse(invoice_line_obj.res_id_resv)
            for invoice_line_detail_obj in invoice_line_obj.invoice_line_detail_ids:
                if not invoice_line_detail_obj.is_commission and not invoice_line_detail_obj.is_point_reward:
                    total_amount += invoice_line_detail_obj.price_subtotal
                elif invoice_line_detail_obj.is_point_reward:
                    total_point_reward += invoice_line_detail_obj.price_subtotal
                if self.is_use_credit_limit and invoice_line_detail_obj.is_commission and debit: ## untuk payment
                    order_type = 3 ## commission
                    if invoice_line_detail_obj.commission_agent_id:
                        agent_id = invoice_line_detail_obj.commission_agent_id.id
                    else:
                        agent_id = self.agent_id.id
                    source_of_fund_type = 'balance'
                    amount_list.append({
                        'amount': invoice_line_detail_obj.price_subtotal,
                        'agent_id': agent_id,
                        'order_type': order_type,
                        'source_of_fund_type': source_of_fund_type,
                        'type': 'debit'
                    })
                elif self.is_use_credit_limit and invoice_line_detail_obj.is_point_reward: ## untuk payment
                    # LANGSUNG POTONG POINT DI RESERVASI AGAR JIKA DI CANCEL PAID TIDAK TERBUAT LEDGER POINT BERKALI-KALI
                    # if debit:
                    #     order_type = 2
                    #     source_of_fund_type = 'point'
                    #     amount_list.append({
                    #         'amount': invoice_line_detail_obj.price_subtotal,
                    #         'agent_id': self.agent_id.id,
                    #         'order_type': order_type,
                    #         'source_of_fund_type': source_of_fund_type,
                    #         'type': 'credit'
                    #     })
                    total_amount -= invoice_line_detail_obj.price_subtotal
        # if not debit:
        #     amount_list.append({
        #         'amount': amount,
        #         'agent_id': self.agent_id.id,
        #         'order_type': 2, ## order
        #         'source_of_fund_type': 'credit_limit'
        #     })
        if total_amount + total_point_reward - self.discount != self.grand_total:
            if debit:
                total_amount += self.grand_total - (total_amount + total_point_reward - self.discount)
            else:
                amount_list.append({
                    'amount': self.grand_total - (total_amount + total_point_reward - self.discount),
                    'agent_id': self.agent_id.id,
                    'order_type': 2,  ## order
                    'source_of_fund_type': 'credit_limit',
                    'info': ', credit limit fee'
                })
        amount_list.append({
            'amount': total_amount - self.discount,
            'agent_id': self.agent_id.id,
            'order_type': 2,  ## order
            'source_of_fund_type': 'credit_limit',
        })
        for rec in amount_list:
            if rec['order_type'] == 2 and rec['source_of_fund_type'] == 'credit_limit' and debit:
                ## CHECK LAGI POINT REWARD HERE
                website_use_point_reward = self.env['ir.config_parameter'].sudo().get_param('use_point_reward')
                if website_use_point_reward == 'True':
                    if book_obj._name == 'tt.reschedule':
                        book_obj = self.env[book_obj.res_model].browse(book_obj.res_id)
                    self.env['tt.point.reward'].add_point_reward(book_obj, total_amount - self.discount, self.env.user.id)
                    ## ASUMSI point reward didapat dari total harga yg di bayar
                    ## karena kalau per pnr per pnr 55 rb & rules point reward kelipatan 10 rb agent rugi 1 point
                    # self.env['tt.point.reward'].add_point_reward(book_obj, agent_check_amount, context['co_uid'])
            ho_invoice_data = {
                'ho_invoice_id': self.id,
                'ho_invoice_model': self._name,
                'pnr': self.pnr,
                'provider_type_id': provider_type_id,
                'display_provider_name': provider

            }
            if book_obj._name == 'tt.reschedule':
                ho_invoice_data.update({
                    'reschedule_id': book_obj.res_id,
                    'reschedule_model': book_obj.res_model
                })
                book_obj = self.env[book_obj.res_model].browse(book_obj.res_id)

            self.env['tt.ledger'].create_ledger_vanilla(
                book_obj._name,
                book_obj.id,
                '%sHO Invoice : %s%s' % ("Payment For " if debit else "",self.name, rec.get('info','')),
                self.name,
                rec['order_type'],
                self.currency_id.id,
                self.env.user.id,
                rec['agent_id'],
                False,
                rec['amount'] if debit == True and rec.get('type', 'debit') == 'debit' else 0,
                rec['amount'] if debit == False or debit == True and rec.get('type','debit') == 'credit' else 0,
                'Ledger for: %s%s' % ("Payment " if debit else "", self.name),
                rec['source_of_fund_type'],
                **ho_invoice_data,
            )

    def action_confirm(self):
        if self.state == 'draft':
            self.state = 'confirm'
            self.confirmed_date = fields.Datetime.now()
            self.confirmed_uid = self.env.user.id

    def create_billing_statement(self):
        if any(rec.state != 'confirm' for rec in self):
            raise UserError(_('You cannot create Billing Statement that an Invoice has been set to \'Confirm\'.'))

        values = {
            # 'payment_term_id': self.payment_term_id.id,
            'due_date': fields.Date.context_today(self),
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
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