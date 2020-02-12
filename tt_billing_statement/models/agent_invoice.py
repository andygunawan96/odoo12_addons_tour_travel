from odoo import fields, models, api, _
import werkzeug
from odoo.exceptions import UserError
from datetime import datetime
import logging, traceback
_logger = logging.getLogger(__name__)


class AgentInvoice(models.Model):
    _inherit = 'tt.agent.invoice'

    billing_statement_id = fields.Many2one('tt.billing.statement', 'Billing Statement', ondelete="set null")
    billing_uid = fields.Many2one('res.users', 'Billed by')

    # CANDY: tambah booker type
    #fixme uncomment later
    # booker_type = fields.Selection(string='Booker Type', related='contact_id.booker_type')

    # Vin Registrasi]
    #fixme uncomment later
    # registration_id = fields.Many2one('res.partner.request', 'Registration')

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

    def action_set_to_confirm_api(self, obj_id, api_context=None):
        invoice_obj = self.browse(int(obj_id))
        if invoice_obj:
            invoice_obj.action_confirm()
            return {
                'error_code': 0,
                'error_msg': "Success",
                'response': {
                    'id': invoice_obj.id,
                    'name': invoice_obj.name,
                    'confirmed_uid': invoice_obj.confirmed_uid.name,
                    'state': invoice_obj.state,
                }
            }
        else:
            return {
                'error_code': 1,
                'error_msg': "No Agent Invoice Found",
                'response': {}
            }

    #manual
    def action_bill(self):
        # security : user_agent_supervisor
        if self.state != 'confirm':
            raise UserError('You can only create Bill Statement from an invoice that has been set to \'Confirm\'.')
        if self.ledger_ids:
            raise UserError('You cannot Bill already Billed Invoice')
        self.state = 'bill'
        self.bill_uid = self.env.user.id
        self.bill_date = fields.Datetime.now()
        self.create_ledger()

    #cron
    def action_bill2(self):
        # security : user_agent_supervisor
        if self.state != 'confirm':
            raise UserError('You can only create Bill Statement from an invoice that has been set to \'Confirm\'.')
        if self.ledger_ids:
            raise UserError('You cannot Bill already Billed Invoice')
        self.state = 'bill2'
        self.bill_uid = self.env.user.id
        self.bill_date = fields.Datetime.now()
        self.create_ledger()


    def action_bill_api(self, obj_id, api_context=None):
        invoice_obj = self.browse(int(obj_id))
        if invoice_obj:
            invoice_obj.action_bill()
            return {
                'error_code': 0,
                'error_msg': "Success",
                'response': {
                    'id': invoice_obj.id,
                    'name': invoice_obj.name,
                    'confirmed_uid': invoice_obj.confirmed_uid.name,
                    'state': invoice_obj.state,
                    'billing_statement_id': {
                        'id': invoice_obj.billing_statement_id.id,
                        'name': invoice_obj.billing_statement_id.name,
                    },
                }
            }
        else:
            return {
                'error_code': 1,
                'error_msg': "No Agent Invoice Found",
                'response': {}
            }

    def create_ledger(self, for_cor=0):
        # create_ledger dilakukan saat state = bill atau bill2
        # JIKA FPO : TIDAK BOLEH CREATE LEDGER
        # if self.contact_id.booker_type == 'FPO':
        #     return True
        # fixme ini mau di apain rulesnya
        # 1. pakai external ID corpor
        # 2. kalau agent_id dan customer_parent_type_id nya berbeda
        if self.customer_parent_type_id == self.env.ref('tt_base.customer_type_fpo'):
            return True

        ledger = self.env['tt.ledger'].sudo()
        amount = 0
        for rec in self.invoice_line_ids:
            amount += rec.total

        vals = ledger.prepare_vals(self._name, self.id, 'Agent Invoice : ' + self.name, self.name, datetime.now(), 2,
                                   self.currency_id.id, self.env.user.id, for_cor == 1 and amount or 0, for_cor == 0 and amount or 0)

        vals['customer_parent_id'] = self.customer_parent_id.id

        ledger.create(vals)

    def action_write_model_api(self, model, rec_id, vals):
        rec_obj = self.env[model].browse(int(rec_id))
        if rec_obj:
            rec_obj.write(vals)
        else:
            return {}

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